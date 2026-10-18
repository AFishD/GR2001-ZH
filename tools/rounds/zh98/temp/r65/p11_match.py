# -*- coding: utf-8 -*-
r"""p11_match.py — 模板匹配 (2x2 块均值 = 轻模糊后降采样, 抹掉重采样的亚像素相位差)。

实拍 PNG 是 583x437 —— **非整数倍**重采样 (583/512=1.1387, 437/448=0.9754) ⇒
同一个字形画在不同 y 上, 像素图案会因亚像素相位不同而不同 (实测: 第二块的同一条 O 行
与第一块的 O 行逐像素差 20 px, 但人眼看是同一个字)。所以判据用**块均值**:
每 2x2 取均值 ⇒ 相位噪声被平掉, 真差异 (不同的字) 保留。
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
DUMP = os.path.join(REPO, 'work', 'builds', 'GR_TEST_PROBE_LEAD', 'temp', 'dump_probe')
SRC = os.path.join(DUMP, 'probe_page.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

bright = (np.asarray(Image.open(SRC).convert('RGB')).mean(axis=2) > 120).astype(float)
print('实拍图 %dx%d' % (bright.shape[1], bright.shape[0]))


def blocksum(y, x, h=16, w=50):
    """16x51 窗口 → 8x26 的 2x2 块均值。"""
    a = bright[y:y + h, x:x + w]
    if a.shape != (h, w):
        return None
    return a.reshape(h // 2, 2, w // 2, 2).mean(axis=(1, 3))


REF_Y, REF_X = 175, 51  # w=50
ref = blocksum(REF_Y, REF_X)
print('模板 = O 行 y%d..%d x%d..%d → %s 块均值 (总墨 %.1f)'
      % (REF_Y, REF_Y + 15, REF_X, REF_X + 50, ref.shape, ref.sum()))

LINES = [('PROBE (标签行)', 161), ('O:   我国山', 175), ('AD:  我国山', 191),
         ('AE:  我国山', 207), ('B0:  我国山', 224), ('B1:  我国山', 240),
         ('S:   B2 B1 B5', 257), ('(下一块) O: 我国山', 305)]
print('\n逐行最佳匹配 (y ±8, x 30..240):')
res = []
for name, y0 in LINES:
    best = None
    for y in range(y0 - 8, y0 + 9):
        if y < 120 or y + 16 > 385:
            continue
        for x in range(30, 240):
            b = blocksum(y, x)
            if b is None:
                continue
            d = float(np.abs(b - ref).sum())
            if best is None or d < best[0]:
                best = (d, y, x)
    d, y, x = best
    res.append((name, d, y, x))
    if name.startswith('B1'):
        v = '★★ 与对照**完全不同** ⇒ lead 0xB1 不是 lead (上界 = 0xB1) ✓'
    elif name.startswith(('S:', 'PROBE')):
        v = '(不是这一组字, 预期高距离)'
    elif name.startswith('(下一块)'):
        v = '★★ 与对照**同一字形组** (第二块探针) ✓'
    elif d <= 8:
        v = '★★ 与对照**同一字形组** ✓'
    else:
        v = '✗ 与对照不同'
    print('  %-18s 最小 L1 %6.1f  y=%3d x=%3d   %s' % (name, d, y, x, v))

print('\n判据: 块均值 L1 ≤ 8 (≈模板总墨 %.0f 的 %.0f%%) 视作"渲染的就是 我 国 山"；'
      '\n      B1 行的值应显著大于 AD/AE/B0。'
      % (ref.sum(), 100.0 * 8 / max(1e-9, ref.sum())))
