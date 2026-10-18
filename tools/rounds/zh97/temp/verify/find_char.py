# -*- coding: utf-8 -*-
r"""find_char.py — 在 drawlog.txt 里找"某一帧画出了含指定字的文本"。

用法: python find_char.py <drawlog.txt> <字...>   [--min-frame N]
输出: 每个字 → 首次/末次出现的帧号 + 前若干条 (帧号, 文本)。
"""
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                       # noqa: E402

CS = tcslib.Charset()


def dec(b):
    out, i = [], 0
    while i < len(b):
        v = b[i]
        if v < 0x80:
            out.append(chr(v)); i += 1
        elif i + 1 < len(b) and (v, b[i + 1]) in CS.pair_of:
            out.append(CS.pair_of[(v, b[i + 1])]); i += 2
        elif v in CS.codes:
            out.append(CS.codes[v]); i += 1
        else:
            i += 1
    return ''.join(out)


def main():
    a = sys.argv[1:]
    p = a[0]
    chars = [c for c in a[1:] if not c.startswith('--')]
    minf = int(a[a.index('--min-frame') + 1]) if '--min-frame' in a else 0
    hits = dict((c, []) for c in chars)
    lastf = 0
    with io.open(p, 'rb') as f:
        for ln in f.read().decode('utf-8', 'replace').splitlines():
            m = re.match(r'F(\d+) ', ln)
            if m:
                lastf = int(m.group(1))
            if '|' not in ln or lastf < minf:
                continue
            try:
                b = bytes(int(x, 16) for x in ln.split('|', 1)[1].split()[:64])
            except Exception:                                      # noqa: BLE001
                continue
            t = dec(b)
            for c in chars:
                if c in t:
                    hits[c].append((lastf, t))
    print('drawlog = %s (末帧 %d)' % (p, lastf))
    for c in chars:
        h = hits[c]
        print('')
        print('「%s」: 命中 %d 条' % (c, len(h)))
        if h:
            print('   帧范围 %d .. %d' % (h[0][0], h[-1][0]))
            seen = set()
            for fr, t in h:
                if fr // 500 in seen:
                    continue
                seen.add(fr // 500)
                print('   F%-6d %s' % (fr, t[:80]))
                if len(seen) >= 12:
                    break


if __name__ == '__main__':
    main()
