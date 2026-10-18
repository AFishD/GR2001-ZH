# -*- coding: utf-8 -*-
r"""m3_bbox.py — round47 ③: 记录矩形的**墨迹包围盒**关系 (判定采样窗到底是 rect 还是 rect+(4,2))。

用**原版没被动过**的记录做判据:
  · ASCII 带 (v0=452 / 482)、手柄图标码 (u=89/136/146, v=395/420) —— 这些是原始字体内容;
  · grid 行 18 (v0=338) 的单字节码 (中 等) —— 它们在 round45 里矩形内被保护过。
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, rects_all, default_rects  # noqa: E402
import numpy as np                                                                 # noqa: E402
import tcslib                                                                      # noqa: E402

DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV
A93 = load('GR_ZH93')
a93 = A93['eng']
rects = rects_all(A93['faces'])


def bbox(img, x0, y0, x1, y1):
    sub = img[max(0, y0):min(H, y1), max(0, x0):min(W, x1)]
    ys, xs = np.where(sub)
    if not len(ys):
        return None
    return (max(0, x0) + int(xs.min()), max(0, y0) + int(ys.min()),
            max(0, x0) + int(xs.max()), max(0, y0) + int(ys.max()))


print('=' * 78)
print('m3: 记录矩形 vs 墨迹包围盒 (GR_ZH93, 原图)')
print('  口径: 在「矩形外扩 ±6/±4」的窗口里找墨, 报 bbox 相对 (u0,v0) 的偏移')
groups = collections.defaultdict(list)
for fname, code, u0, v0, u1, v1 in rects:
    if u1 <= u0 or v1 <= v0:
        continue
    bb = bbox(a93, u0 - 6, v0 - 4, u1 + 6, v1 + 4)
    if bb is None:
        groups['无墨'].append((fname, code, u0, v0, u1, v1))
        continue
    key = (fname, v0, u1 - u0, v1 - v0)
    groups[key].append((code, u0,
                        bb[0] - u0, bb[1] - v0, bb[2] - u0, bb[3] - v0))
for k in sorted(groups, key=lambda z: (str(z[0]), z[1] if isinstance(z, tuple) and len(z) > 1 else 0)):
    v = groups[k]
    if k == '无墨':
        print('  [无墨] %d 条: %s' % (len(v), [(x[0], hex(x[1]), x[2], x[3]) for x in v[:6]]))
        continue
    fname, v0, w, h = k
    d = collections.Counter((x[2], x[3], x[4], x[5]) for x in v)
    print('  face=%-8s v0=%-4d %dx%d  %d 条; bbox 偏移分布 (dx0,dy0,dx1,dy1): %s'
          % (fname, v0, w, h, len(v), d.most_common(6)))

print()
print('=' * 78)
print('逐条明细 (default face, 按 v0 分组):')
dflt = default_rects(A93['faces'])
for v0 in sorted(set(v[1] for v in dflt.values())):
    print('  --- v0=%d ---' % v0)
    for code, (u0, vv0, u1, v1) in sorted(dflt.items(), key=lambda kv: kv[1][0]):
        if vv0 != v0:
            continue
        bb = bbox(a93, u0 - 6, v0 - 4, u1 + 6, v1 + 4)
        s = ('bbox 偏移 (%3d,%3d,%3d,%3d)' % (bb[0] - u0, bb[1] - v0, bb[2] - u0, bb[3] - v0)
             if bb else '无墨')
        print('    0x%02X u=%4d..%4d v=%4d..%4d  %s' % (code, u0, u1, v0, v1, s))

# ---------- 中 0xD6 的形状: 逐像素 ----------
print()
print('=' * 78)
print('中 0xD6: 把「矩形」和「矩形+(4,2) 窗」两种假设下的 16x16 都打出来')
u0, v0, u1, v1 = dflt[0xD6]
print('  矩形 u=%d..%d v=%d..%d' % (u0, u1, v0, v1))
for tag, (x0, y0) in (('rect (u0,v0)', (u0, v0)), ('rect+(4,2)', (u0 + DU, v0 + DV)),
                      ('rect+(0,2)', (u0, v0 + DV)), ('rect+(2,0)', (u0 + 2, v0))):
    print('  --- 假设 %s → 窗 x=%d..%d y=%d..%d ---' % (tag, x0, x0 + 15, y0, y0 + 15))
    for y in range(y0, y0 + 16):
        print('     %4d |%s|' % (y, ''.join('#' if a93[y, x] else '.' for x in range(x0, x0 + 16))))
