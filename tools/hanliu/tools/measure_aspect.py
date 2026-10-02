# [hanliu 收编] 原件: C:/gr_build/tmp/zh8b/measure_aspect.py (逐字复制)。原件保留于原处未动。
# -*- coding: utf-8 -*-
"""measure_aspect.py — Controller 页 f33480 左/右列 12px 对字 屏显墨宽高比直接测量
用法: python measure_aspect.py <snap_f00033480.png> <tag>
方法: 行带二值化 → 列剖面连通簇 (无位置模型) → 每簇 bbox 宽高 (snap→game: ×(1/0.911, 1/0.975))
      墨簇宽 8..30 snap px 视为一个字形; 与 atlas 模板墨 bbox (≈11×11) 对照。
期望: v7 左列 ≈1.0 (v6 缺陷 ≈1.6); 右列两版都 ≈1.0。
"""
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SNAP, TAG = sys.argv[1], sys.argv[2]
SX, SY = 0.911, 0.975
ROWS = [(110, 'L'), (135, 'L'), (160, 'L'), (185, 'L'), (210, 'L'),
        (235, 'L'), (260, 'L'), (285, 'L'), (310, 'L'), (335, 'L'),
        (110, 'R'), (135, 'R'), (160, 'R'), (185, 'R'), (210, 'R'),
        (235, 'R'), (260, 'R'), (285, 'R'), (310, 'R'), (335, 'R')]
XL, XR = (100, 360), (370, 560)   # 左/右列 x 搜索窗 (snap px)

im = np.asarray(Image.open(SNAP).convert('L'), dtype=float)
all_asp = []
for ri, (y0, col) in enumerate(ROWS):
    lo, hi = (XL if col == 'L' else XR)
    band = im[y0 - 2:y0 + 16, lo:hi]
    ink = band > 110.0
    prof = ink.sum(axis=0)
    # 连通簇 (允许 1px 空隙)
    clusters, s = [], None
    gap = 0
    for x in range(len(prof)):
        if prof[x] > 0:
            if s is None: s = x
            gap = 0
        elif s is not None:
            gap += 1
            if gap >= 2:
                clusters.append((s, x - gap + 1)); s = None; gap = 0
    if s is not None: clusters.append((s, len(prof)))
    out = []
    for (a, b) in clusters:
        w = b - a
        if not (8 <= w <= 30): continue
        sub = ink[:, a:b]
        ys, xs = np.where(sub)
        if len(ys) < 12: continue
        h = ys.max() - ys.min() + 1
        # 模板 = 11×11 墨 (Zpix); 屏显 game px
        gw, gh = w / SX, h / SY
        asp = gw / gh
        out.append((a + lo, w, h, round(asp, 2)))
        all_asp.append(asp)
    if out:
        print('%s %s row%02d y=%d: %s' % (TAG, col, ri, y0,
              ' '.join('x%d w%dh%d a%.2f' % o for o in out)))
a = np.array(all_asp)
print('[%s] 簇数=%d aspect 均值=%.2f 中位=%.2f min=%.2f max=%.2f' %
      (TAG, len(a), a.mean(), np.median(a), a.min(), a.max()))
