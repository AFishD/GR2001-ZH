# -*- coding: utf-8 -*-
r"""v15_timeline.py — 抓帧时间线: 用粗特征给每帧归类, 打印"画面切换"时刻。"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
for d in sys.argv[1:]:
    fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
    print('=' * 78)
    print('%s: %d 帧' % (d, len(fs)))
    prev = None
    start = None
    for f in fs:
        im = Image.open(os.path.join(d, f)).convert('L').resize((16, 12), Image.BOX)
        a = (np.asarray(im) // 32).astype(np.uint8)
        sig = a.tobytes()
        if sig != prev:
            n = int(''.join(ch for ch in f if ch.isdigit()))
            if start is not None:
                print('   f%-6d .. f%-6d  (画面 A)' % (start, n - 100 if n > start else start))
            start = n
            prev = sig
    print('   f%-6d .. 结束' % start)
