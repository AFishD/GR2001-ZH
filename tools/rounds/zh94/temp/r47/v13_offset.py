# -*- coding: utf-8 -*-
r"""v13_offset.py — 判定「引擎采样窗」相对记录矩形的 (dx,dy) 偏置 (用 ZH93 实机截图)。

对若干**已知正确显示**的单字节记录码字形, 把图集里 (u0+dx, v0+dy) 的 16x16 窗口
拿去截图里做 0 误差滑窗匹配, 看哪个 (dx,dy) 命中 ⇒ 那个 (dx,dy) 就是引擎采样窗。
"""
import os
import sys

import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from r47lib import load                                                    # noqa: E402

eng = load('GR_ZH93')['eng']
SHOT = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'M18_详情页_全屏.png')
im = np.asarray(Image.open(SHOT).convert('L'))
bright = (im > 128)          # 描述框 = 暗底亮字
dark = (im < 128)

CANDS = [('后', 0xDB, 0, 354), ('向', 0xE1, 96, 354), ('装', 0xE4, 144, 354),
         ('有', 0xFB, 480, 354), ('雷', 0xFC, 496, 354), ('的', 0xAF, 16, 178),
         ('中', 0xD6, 912, 338), ('是', 0xD9, 960, 338), ('斗', 0xD8, 944, 338)]

print('截图 %s %s' % (os.path.basename(SHOT), im.shape))
for ch, code, u0, v0 in CANDS:
    print('=' * 70)
    print('「%s」0x%02X 记录格 (%d,%d)' % (ch, code, u0, v0))
    for dy in (-1, 0, 1, 2):
        for dx in (0, 4):
            x0, y0 = u0 + dx, v0 + dy
            if y0 < 0 or y0 + 16 > 512:
                continue
            tpl = eng[y0:y0 + 16, x0:x0 + 16]
            n = int(tpl.sum())
            if n == 0:
                continue
            hits = []
            for tag, mask in (('亮字', bright), ('暗字', dark)):
                sw = sliding_window_view(mask.astype(np.uint8), (16, 16))
                cnt = sw.sum(axis=(2, 3))
                h = np.argwhere((cnt == n) & (sw == tpl).all(axis=(2, 3)))
                if len(h):
                    hits.append((tag, [(int(x), int(y)) for y, x in h[:5]]))
            if hits:
                print('   (dx=%+d, dy=%+d) 命中: %s' % (dx, dy, hits))
    # 该格"末两行"的差异情况 (决定 dy=0 与 dy=1 能不能区分)
    a = eng[v0 + 15, u0:u0 + 16]
    b = eng[v0 + 16, u0:u0 + 16] if v0 + 16 < 512 else None
    print('   末行 (v0+15) 墨 %d 个; 下一行 (v0+16) 墨 %s ⇒ dy 可区分: %s'
          % (a.sum(), b.sum() if b is not None else '-', b is not None and not (a == b).all()))
