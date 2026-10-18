# -*- coding: utf-8 -*-
r"""m5_table.py — round47 ⑤: 全表逐条记录的「墨迹相对矩形偏移」, 找出写字形的口径。

同时: 中/抖 的码位、以及 0xD2..0xFE 这些单字节汉字记录的偏移分布。
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, default_rects   # noqa: E402
import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402

A93 = load('GR_ZH93')
a93 = A93['eng']
dflt = default_rects(A93['faces'])
cs = tcslib.Charset()
print('=' * 78)
print('中 / 抖 的码位:')
for ch in ('中', '抖'):
    single = cs.enc_single.get(ch)
    pair = cs.enc_pair.get(ch)
    print('  %s: 单字节=%s 对偶=%s' % (ch, ('0x%02X' % single) if single else None, pair))
    if single:
        u0, v0, u1, v1 = dflt[single]
        print('     记录矩形 u=%d..%d v=%d..%d' % (u0, u1, v0, v1))
    if pair:
        s = tcslib.pair_slot(*pair)
        print('     对偶槽 %d (row%d col%d) → 引擎格 x=%d y=%d'
              % (s, s // NCOL, s % NCOL, CW * (s % NCOL), yrow(s // NCOL)))

print()
print('=' * 78)
print('每个 v0 组: 墨迹包围盒相对 (u0,v0) 的偏移  (只在 右扩8/下扩6 里找墨; dx1>=16 = 混进邻居)')
tab = []
for code, (u0, v0, u1, v1) in sorted(dflt.items()):
    sub = a93[v0:v1 + 6, u0:u1 + 8]
    ys, xs = np.where(sub)
    if not len(ys):
        tab.append((code, u0, v0, u1 - u0, v1 - v0, None))
        continue
    tab.append((code, u0, v0, u1 - u0, v1 - v0,
                (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))))
byv0 = collections.defaultdict(list)
for row in tab:
    byv0[row[2]].append(row)
for v0 in sorted(byv0):
    print('  --- v0=%d (%d 条) ---' % (v0, len(byv0[v0])))
    c = collections.Counter(r[5] for r in byv0[v0])
    print('      偏移分布 (dx0,dy0,dx1,dy1): %s' % c.most_common(8))
    for code, u0, v0, w, h, bb in byv0[v0]:
        ch = None
        for ch2, b in cs.enc_single.items():
            if b == code:
                ch = ch2
                break
        print('      0x%02X u=%4d %2dx%2d %-3s %s' % (code, u0, w, h, ch or '',
                                                     ('(%3d,%3d,%3d,%3d)' % bb) if bb else '无墨'))

# 0xD2..0xFE 的横向位置: 用"列"看 (x0 = u0+dx0)
print()
print('=' * 78)
print('单字节汉字码 (0xAF..0xFE) 的 dx0/dy0 直方图:')
h = collections.Counter()
for code, u0, v0, w, hh, bb in tab:
    if 0xAF <= code <= 0xFE and bb:
        h[(w, hh, bb[0], bb[1])] += 1
for k, v in sorted(h.items()):
    print('   矩形 %2dx%2d  墨迹 dx0=%2d dy0=%2d  → %d 条' % (k[0], k[1], k[2], k[3], v))
