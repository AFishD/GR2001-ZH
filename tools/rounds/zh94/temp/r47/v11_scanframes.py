# -*- coding: utf-8 -*-
r"""v11_scanframes.py — 在**已有**的实机抓帧里搜「中」等记录码字形 (1:1 渲染, 可直接模板匹配)。

用途: 若某帧里出现「中」, 就能直接读出"引擎显示的是图集哪一行" ⇒ 顺便判定采样窗口径。
"""
import io
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

eng = load('GR_ZH94')['eng']
CODES = [('中', 0xD6, 912, 338), ('斗', 0xD8, 944, 338), ('是', 0xD9, 960, 338),
         ('有', 0xFB, 480, 354), ('后', 0xDB, 0, 354)]
tpls = {}
for ch, code, u0, v0 in CODES:
    tpls[ch] = (eng[v0:v0 + 16, u0:u0 + 16], code, u0, v0)

dirs = sys.argv[1:] or [os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'dump_r46w')]
for d in dirs:
    if not os.path.isdir(d):
        print('跳过 (不存在): %s' % d)
        continue
    fs = sorted(f for f in os.listdir(d) if f.endswith('.png'))
    print('=' * 78)
    print('%s: %d 帧' % (d, len(fs)))
    for name in fs:
        a = np.asarray(Image.open(os.path.join(d, name)).convert('L'))
        dark = a < 128
        sw = sliding_window_view(dark.astype(np.uint8), (16, 16))
        cnt = sw.sum(axis=(2, 3))
        for ch, (tpl, code, u0, v0) in tpls.items():
            n = int(tpl.sum())
            hit = np.argwhere((cnt == n) & (sw == tpl).all(axis=(2, 3)))
            if len(hit):
                print('  %s: 「%s」(0x%02X) 命中 %d 处: %s'
                      % (name, ch, code, len(hit), [(int(x), int(y)) for y, x in hit[:6]]))
