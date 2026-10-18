# -*- coding: utf-8 -*-
r"""p12_refine.py — 亚像素对齐后的模板匹配 (最终定量判据)。

上一版 (整数像素) 受"非整数倍重采样"的相位噪声影响: 同一组字在不同 y 上 L1 = 10~19,
不同的字 = 28~31, 分得开但不好看。这里把 y 方向做**线性插值的亚像素平移**再比,
同一组字的残差应掉到接近 0。
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

img = (np.asarray(Image.open(SRC).convert('RGB')).mean(axis=2) > 120).astype(float)
H, W = img.shape
print('实拍图 %dx%d' % (W, H))
TH, TW = 16, 50


def win(y, x, dy=0.0):
    """窗口 (y+dy, x) 处的 THxTW 灰度 (y 方向线性插值)。"""
    y0 = int(np.floor(y + dy))
    f = (y + dy) - y0
    if y0 < 0 or y0 + TH + 1 > H or x < 0 or x + TW > W:
        return None
    a = img[y0:y0 + TH, x:x + TW]
    b = img[y0 + 1:y0 + 1 + TH, x:x + TW]
    return a * (1 - f) + b * f


REF_Y, REF_X = 175, 51
ref = win(REF_Y, REF_X)
print('模板 = O 行 (y=%d, x=%d) 的 %dx%d 位图, 墨 %.0f px' % (REF_Y, REF_X, TW, TH, ref.sum()))

LINES = [('PROBE (标签行)', 161), ('O:   我国山', 175), ('AD:  我国山', 191),
         ('AE:  我国山', 207), ('B0:  我国山', 224), ('B1:  我国山', 240),
         ('S:   B2 B1 B5', 257), ('(下一块) O: 我国山', 305)]
print('\n逐行**亚像素**最佳匹配 (y ±9 步长 0.125, x 30..240 整数):')
rows = []
for name, y0 in LINES:
    best = None
    for x in range(30, 240):
        for dy in np.arange(-9.0, 9.01, 0.125):
            w = win(y0, x, dy)
            if w is None:
                continue
            d = float(np.abs(w - ref).sum())
            if best is None or d < best[0]:
                best = (d, y0 + dy, x)
    d, y, x = best
    rows.append((name, d, y, x))
    if name.startswith('B1'):
        v = '★★ 与对照**完全不同** ⇒ lead 0xB1 不是 lead (上界 = 0xB1) ✓'
    elif name.startswith(('S:', 'PROBE')):
        v = '(不是这一组字 ⇒ 预期高残差)'
    elif name.startswith('(下一块)'):
        v = '★★ 与对照**同一字形组** ✓'
    elif d <= 6:
        v = '★★ 与对照**同一字形组** ⇒ 该 lead 可用 ✓'
    else:
        v = '✗ 与对照不同'
    print('  %-18s 残差 %6.2f px  y=%7.3f x=%3d   %s' % (name, d, y, x, v))

same = [r[1] for r in rows if r[0].startswith(('O:', 'AD', 'AE', 'B0', '(下一块)'))]
diff = [r[1] for r in rows if r[0].startswith(('B1', 'S:', 'PROBE'))]
print('\n"同一组字"的残差: %s  (最大 %.2f)' % (['%.2f' % x for x in same], max(same)))
print('"不同内容"的残差: %s  (最小 %.2f)' % (['%.2f' % x for x in diff], min(diff)))
print('⇒ 分离度 = %.1f 倍' % (min(diff) / max(0.01, max(same))))
