# -*- coding: utf-8 -*-
r"""v17_cursor.py — 逐帧找"金色高亮条"所在行 (主菜单/列表光标)。"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = sys.argv[1]
x0, x1 = int(sys.argv[2]), int(sys.argv[3])
f0, f1 = int(sys.argv[4]), int(sys.argv[5])
prev = None
for f in sorted(os.listdir(d)):
    if not (f.startswith('snap_') and f.endswith('.png')):
        continue
    n = int(''.join(ch for ch in f if ch.isdigit()))
    if n < f0 or n > f1:
        continue
    a = np.asarray(Image.open(os.path.join(d, f)).convert('RGB')).astype(int)
    sub = a[20:410, x0:x1]
    gold = (sub[:, :, 0] > 140) & (sub[:, :, 1] > 90) & (sub[:, :, 1] < 215) & (sub[:, :, 2] < 130)
    cnt = gold.sum(axis=1)
    if cnt.max() < 40:
        y = -1
    else:
        y = int(np.argmax(cnt)) + 20
    if prev is None or abs(y - prev) > 3:
        print('  f%-6d 金色高亮行 y≈%-5d (该行金色像素 %d)' % (n, y, int(cnt.max())))
        prev = y
