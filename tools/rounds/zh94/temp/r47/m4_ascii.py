# -*- coding: utf-8 -*-
r"""m4_ascii.py — round47 ④: 用**原版 ASCII 带**的记录矩形判定「记录矩形 vs 采样窗」的偏置。

ASCII 带 (v0=452) 是原版字体内容 (我们所有补丁都没碰过, 而且游戏里显示正确),
所以「记录矩形」与「墨迹」的相对关系 = 原版字体工具的约定 = 引擎采样窗。
"""
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
DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV

for ch in 'AWgypQ1|_':
    code = ord(ch)
    u0, v0, u1, v1 = dflt[code]
    w = u1 - u0
    print('=' * 78)
    print("'%s' 0x%02X 记录矩形 u=%d..%d v=%d..%d (%dx%d)" % (ch, code, u0, u1, v0, v1, w, v1 - v0))
    print('   [矩形右扩 6, 下扩 4] 的墨迹:  (列尺 = 相对 u0 的偏移)')
    print('        ' + ''.join(('%d' % (d % 10)) if d % 8 == 0 else ' '
                                for d in range(-2, w + 7)))
    for y in range(v0 - 3, v1 + 5):
        line = ''.join('#' if a93[y, u0 + d] else '.' for d in range(-2, w + 7))
        d = y - v0
        print('   dy=%+3d |%s|%s' % (d, line, '  <= 记录矩形顶' if d == 0 else
                                     ('  <= 记录矩形底(不含)' if d == v1 - v0 else '')))
    # 墨迹包围盒 (只在矩形右/下扩 6/4 的区域里找, 左/上不扩 ⇒ 邻居的墨不会混进来)
    sub = a93[v0:v1 + 4, u0:u1 + 6]
    ys, xs = np.where(sub)
    if len(ys):
        print('   墨迹包围盒: u0%+d..u0%+d  v0%+d..v0%+d   (绝对 u=%d..%d v=%d..%d)'
              % (xs.min(), xs.max(), ys.min(), ys.max(), u0 + xs.min(), u0 + xs.max(),
                 v0 + ys.min(), v0 + ys.max()))
        print('   → 相对「矩形」: 左%d 上%d 右%d 下%d ;  相对「矩形+(4,2)」: 左%d 上%d'
              % (xs.min(), ys.min(), xs.max() - (w - 1), ys.max() - (v1 - v0 - 1),
                 xs.min() - DU, ys.min() - DV))
