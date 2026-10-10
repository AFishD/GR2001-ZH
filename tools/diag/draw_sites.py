# -*- coding: utf-8 -*-
r"""draw_sites.py — 按 RA 前缀列 DrawString 站点 (会话工具)
用法: python draw_sites.py <drawlog> <PC前缀如219A70> <RA前缀如2B> [f0 f1]
"""
import collections
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
cs = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
pairs = {tuple(v): k for k, v in cs['pair_of'].items()}
leads = {v[0] for v in cs['pair_of'].values()}
codes = {int(v): k for k, v in cs['codes'].items()}
RE = re.compile(r'^F(\d+) PC=([0-9A-Fa-f]+)(?: RA=([0-9A-Fa-f]+))?(.*?)\|\s*([0-9A-Fa-f ]*)$')
KV = re.compile(r'([0-9A-Za-z]+)=([0-9A-Fa-f]+)')


def dec(raw):
    out, i = [], 0
    while i < len(raw):
        b = raw[i]
        if b in leads and i + 1 < len(raw) and (b, raw[i + 1]) in pairs:
            out.append(pairs[(b, raw[i + 1])]); i += 2
        elif b in codes:
            out.append(codes[b]); i += 1
        elif 0x20 <= b < 0x7F:
            out.append(chr(b)); i += 1
        else:
            i += 1
    return ''.join(out)


def main():
    path, pcpre, rap = sys.argv[1], sys.argv[2].upper(), sys.argv[3].upper()
    f0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
    f1 = int(sys.argv[5]) if len(sys.argv) > 5 else 10 ** 9
    cnt = collections.Counter()
    samples = {}
    with open(path, encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = RE.match(ln.rstrip('\n'))
            if not m:
                continue
            fr, pc, ra = int(m.group(1)), m.group(2).upper(), (m.group(3) or '').upper()
            if not (f0 <= fr <= f1) or not pc.startswith(pcpre) or not ra.startswith(rap):
                continue
            d = dict(KV.findall(m.group(4)))
            raw = bytes.fromhex(m.group(5).replace(' ', '')) if m.group(5).strip() else b''
            z = 0
            while z + 1 < len(raw) and not (raw[z] == 0 and raw[z + 1] == 0):
                z += 2
            txt = dec(raw[:z])
            y = ('%.1f' % struct.unpack('>f', struct.pack('>I', int(d['F13'], 16)))[0]) if 'F13' in d else '-'
            x = ('%.1f' % struct.unpack('>f', struct.pack('>I', int(d['F12'], 16)))[0]) if 'F12' in d else '-'
            k = (ra, x, y, txt)
            cnt[k] += 1
            samples.setdefault(k, fr)
    print('# %s  PC^=%s RA^=%s  F[%d,%d]  站点(RA,x,y,文本) %d 种' % (path, pcpre, rap, f0, f1, len(cnt)))
    for (ra, x, y, txt), c in sorted(cnt.items(), key=lambda kv: (kv[0][0], kv[0][2])):
        print('  RA=%-7s x=%-7s y=%-7s ×%-6d 首F%-6d %s' % (ra, x, y, c, samples[(ra, x, y, txt)], txt))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
