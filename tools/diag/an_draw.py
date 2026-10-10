# -*- coding: utf-8 -*-
r"""an_draw.py — drawlog 解码器 (会话工具, 不入库)

用法:
  python an_draw.py <drawlog.txt> text [--pc 219EB0,219A70] [--ra X] [--f0 N --f1 N]
  python an_draw.py <drawlog.txt> grep <子串>          # 解码后按文本过滤 (含上下文帧号)
  python an_draw.py <drawlog.txt> susp                 # 列出可疑串 (孤 lead / 毒字节 / 控制字节)
  python an_draw.py <drawlog.txt> keys                 # 只统计 PC/RA 组合
说明: drawlog 行形如
  F3303 PC=219EB0 RA=21DA28 THIS=.. STR=005AACDA A2=.. A3=.. F12=41D00000 F13=3F800000 ... | <hex>
F12/F13 = 单精度 x/y; 串体 = `|` 后的十六进制, 到 00 00 结束 (引擎按 C 串消费)。
"""
import argparse
import collections
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

RE_HDR = re.compile(r'^F(\d+) PC=([0-9A-Fa-f]+)(?: RA=([0-9A-Fa-f]+))?(.*?)\s*\|\s*([0-9A-Fa-f ]*)$')
RE_KV = re.compile(r'([0-9A-Za-z]+)=([0-9A-Fa-f]+)')


class Dec:
    def __init__(self, path=CHARSET):
        cs = json.load(open(path, encoding='utf-8'))
        self.codes = {int(v): k for k, v in cs['codes'].items()}
        self.pairs = {tuple(v): k for k, v in cs['pair_of'].items()}
        self.leads = {v[0] for v in cs['pair_of'].values()}

    def text(self, raw, mark=False):
        out, i, bad = [], 0, []
        while i < len(raw):
            b = raw[i]
            if b in self.leads and i + 1 < len(raw) and (b, raw[i + 1]) in self.pairs:
                out.append(self.pairs[(b, raw[i + 1])])
                i += 2
            elif b in self.codes:
                out.append(self.codes[b])
                i += 1
            elif 0x20 <= b < 0x7F:
                out.append(chr(b))
                i += 1
            elif b == 0:
                break
            else:
                out.append('[%02X]' % b)
                bad.append(b)
                i += 1
        return ''.join(out), bad


def cstr(hexs):
    raw = bytes.fromhex(hexs.replace(' ', '')) if hexs.strip() else b''
    # 引擎按 C 串消费: 截到 0x0000
    z = 0
    while z + 1 < len(raw) and not (raw[z] == 0 and raw[z + 1] == 0):
        z += 2
    return raw[:z]


def flt(h):
    try:
        return struct.unpack('>f', struct.pack('>I', int(h, 16)))[0]
    except Exception:
        return float('nan')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('log')
    ap.add_argument('mode', choices=('text', 'grep', 'susp', 'keys'))
    ap.add_argument('needle', nargs='?', default='')
    ap.add_argument('--pc', default='219EB0,219A70')
    ap.add_argument('--ra', default='')
    ap.add_argument('--f0', type=int, default=None)
    ap.add_argument('--f1', type=int, default=None)
    ap.add_argument('--limit', type=int, default=400)
    a = ap.parse_args()
    pcs = {p.upper().lstrip('0') or '0' for p in a.pc.split(',') if p}
    dec = Dec()
    n, keys = 0, collections.Counter()
    with open(a.log, 'r', encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = RE_HDR.match(ln.rstrip('\n'))
            if not m:
                continue
            fr, pc, ra, kv, hexs = m.group(1), m.group(2).upper(), (m.group(3) or '').upper(), m.group(4), m.group(5)
            keys[(pc, ra)] += 1
            if a.mode == 'keys':
                continue
            if a.mode in ('text', 'grep', 'susp') and pcs and (pc.lstrip('0') or '0') not in pcs:
                continue
            if a.ra and ra != a.ra.upper():
                continue
            if a.f0 is not None and not (a.f0 <= int(fr) <= (a.f1 if a.f1 is not None else a.f0)):
                continue
            d = dict(RE_KV.findall(kv))
            txt, bad = dec.text(cstr(hexs))
            if a.mode == 'grep' and a.needle not in txt:
                continue
            if a.mode == 'susp' and not bad:
                continue
            x = flt(d['F12']) if 'F12' in d else None
            y = flt(d['F13']) if 'F13' in d else None
            print('F%-6s PC=%s RA=%-6s x=%-7s y=%-7s %s%s'
                  % (fr, pc, ra, ('%.1f' % x) if x is not None else '-',
                     ('%.1f' % y) if y is not None else '-', txt,
                     ('   <BAD %s>' % ' '.join('%02X' % b for b in bad)) if bad else ''))
            n += 1
            if n >= a.limit:
                print('# ... (limit %d)' % a.limit)
                break
    if a.mode == 'keys':
        for (pc, ra), c in keys.most_common(40):
            print('%-8s %-8s %d' % (pc, ra, c))
    print('# 命中 %d 行' % n, file=sys.stderr)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
