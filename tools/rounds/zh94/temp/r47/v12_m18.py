# -*- coding: utf-8 -*-
r"""v12_m18.py — 用**已有的 ZH93 实机截图**判定采样窗口到底是不是"记录矩形那 16 行"。

思路: 截图里「地雷在正后方会」含单字节码 0xDB「后」, 它的格子 = 图集 (0..15, 354..369),
      模板 err=0 ⇒ 格子 16 行 == 字体模板 16 行。
      若引擎采样 [v0, v1)  ⇒ 渲染出来的 16 行 == 图集 354..369;
      若引擎采样 [v0+1, v1+1) ⇒ 渲染 == 图集 355..370 (第 1 行不同, 末行换成 370)。
      两者在"末行"上不同 ⇒ 直接读截图就能定论。
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

eng93 = load('GR_ZH93')['eng']
SHOTS = [os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'M18_详情页_全屏.png'),
         os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'M18_译文_实机_GR_ZH93.png'),
         os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', '武器列表页_全屏.png')]

# 候选字符 (行 19 的单字节记录码, 格子 16x16, err=0)
CANDS = [('后', 0xDB, 0, 354), ('向', 0xE1, 96, 354), ('装', 0xE4, 144, 354),
         ('有', 0xFB, 480, 354), ('雷', 0xFC, 496, 354), ('爆', 0xEB, 240, 354),
         ('选', 0xEC, 256, 354), ('更', 0xF9, 448, 354), ('的', 0xAF, 16, 178),
         ('中', 0xD6, 912, 338)]

for p in SHOTS:
    if not os.path.isfile(p):
        print('缺 %s' % p)
        continue
    im = np.asarray(Image.open(p).convert('L'))
    print('=' * 78)
    print('%s  %s' % (os.path.basename(p), im.shape))
    for ch, code, u0, v0 in CANDS:
        tpl = eng93[v0:v0 + 16, u0:u0 + 16]
        n = int(tpl.sum())
        if n == 0:
            continue
        for tag, mask in (('暗底亮字', im > 128), ('亮底暗字', im < 128)):
            sw = sliding_window_view(mask.astype(np.uint8), (16, 16))
            cnt = sw.sum(axis=(2, 3))
            hit = np.argwhere((cnt == n) & (sw == tpl).all(axis=(2, 3)))
            if len(hit):
                y, x = int(hit[0][0]), int(hit[0][1])
                print('  「%s」0x%02X (%s): 0 误差命中 %d 处, 首个 = 屏幕 (%d, %d)'
                      % (ch, code, tag, len(hit), x, y))
                # 打印屏幕 18 行 vs 图集 352..371
                print('     屏幕那 16 行 (y=%d..%d):' % (y, y + 15))
                scr = mask[y:y + 16, x:x + 16]
                for k in range(16):
                    print('        scr%2d |%s|' % (k, ''.join('#' if scr[k, i] else '.'
                                                              for i in range(16))))
                print('     图集 (x=%d..%d) y=352..371:' % (u0, u0 + 15))
                for yy in range(v0 - 2, v0 + 18):
                    mark = ''
                    if yy == v0:
                        mark = ' ← v0 (模型 A 首行)'
                    elif yy == v0 + 1:
                        mark = ' ← v0+1 (模型 B 首行)'
                    elif yy == v0 + 15:
                        mark = ' ← 模型 A 末行'
                    elif yy == v0 + 16:
                        mark = ' ← 模型 B 末行'
                    print('        at%3d |%s|%s' % (yy, ''.join('#' if eng93[yy, xx] else '.'
                                                                for xx in range(u0, u0 + 16)), mark))
                break
