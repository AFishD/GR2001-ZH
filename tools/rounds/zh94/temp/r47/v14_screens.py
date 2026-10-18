# -*- coding: utf-8 -*-
r"""v14_screens.py — 把抓帧按"画面变化"分段 (每段给一帧代表), 用来核对导航走到哪一步。"""
import hashlib
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = sys.argv[1]
fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
prev = None
segs = []
for i, f in enumerate(fs):
    a = np.asarray(Image.open(os.path.join(d, f)).convert('L'))
    h = hashlib.sha1(a.tobytes()).hexdigest()[:12]
    if h != prev:
        segs.append((f, h, i))
        prev = h
print('%s: %d 帧 → %d 个不同画面' % (d, len(fs), len(segs)))
for f, h, i in segs:
    print('  %-24s (第 %d 帧)  %s' % (f, i, h))
