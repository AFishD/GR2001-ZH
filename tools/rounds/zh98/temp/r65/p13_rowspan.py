# -*- coding: utf-8 -*-
r"""p13_rowspan.py — 逐 **y 行**打印正文框里墨的横向范围 (最左/最右 x + 墨像素数)。

这样不依赖"行带切分": 一张表就能看出每一行渲染了几个字形块
(3 个汉字 = 宽 ~51px; 6 个字形块 = 宽 ~111px), 以及 B1 行为什么更宽。
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

bright = np.asarray(Image.open(SRC).convert('RGB')).mean(axis=2) > 120
X0, X1 = 30, 290
LABEL = 'ASCII 标签宽 8px/字'
print('x 扫描区间 %d..%d;  %s;  1 个汉字 = 16px' % (X0, X1, LABEL))
print('\n y   墨px  xmin  xmax  宽px  ≈汉字数   备注')
for y in range(150, 285):
    row = bright[y, X0:X1]
    n = int(row.sum())
    if n == 0:
        print(' %3d     0     -     -     -       -' % y)
        continue
    xs = np.where(row)[0]
    a, b = X0 + xs[0], X0 + xs[-1]
    print(' %3d  %4d  %4d  %4d  %4d   %5.1f' % (y, n, a, b, b - a + 1, (b - a + 1) / 16.0))
