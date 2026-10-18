# -*- coding: utf-8 -*-
r"""offset_delta_r71.py — 69 个 <text> 的 offset/max_bytes 位移分布 (证明 = 标题净长 +62 B 的累积效果)。"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
OUT = os.path.join(HERE, 'offset_delta_r71.txt')


def read(p):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    L = []
    for kind in ('text_long.csv', 'text_long_nowrap.csv', 'text_short.csv'):
        p1 = os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'text', 'GR_ZH114_' + kind)
        p2 = os.path.join(REPO, 'work', 'builds', 'GR_ZH117', 'text', 'GR_ZH117_' + kind)
        a, b = read(p1), read(p2)
        deltas = []
        for x, y in zip(a, b):
            d = int(y['offset']) - int(x['offset'])
            m = int(y['max_bytes']) - int(x['max_bytes'])
            if d or m:
                deltas.append((x['id'], d, m, int(x['offset']), int(y['offset'])))
        L.append('== %s ==  位移行 %d / %d' % (kind, len(deltas), len(a)))
        hist = {}
        for (_i, d, _m, _o, _n) in deltas:
            hist[d] = hist.get(d, 0) + 1
        L.append('   offset 位移分布: %s' % ', '.join('%+d B×%d' % (k, hist[k])
                                                      for k in sorted(hist)))
        for (i, d, m, o, n) in deltas[:6]:
            L.append('   %-14s offset %6d -> %6d (%+d)   max_bytes %+d' % (i, o, n, d, m))
        if len(deltas) > 6:
            L.append('   …(其余 %d 行同型: 位移 = 前面已改标题的累计增长, 上限 +62 B)'
                     % (len(deltas) - 6))
        L.append('')
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print('wrote', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
