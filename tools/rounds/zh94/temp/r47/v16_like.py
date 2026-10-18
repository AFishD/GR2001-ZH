# -*- coding: utf-8 -*-
r"""v16_like.py — 找出与某一参考帧"同一画面"的帧区间 (粗相似度)。"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = sys.argv[1]
ref = sys.argv[2]
thr = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
r = np.asarray(Image.open(os.path.join(d, ref)).convert('L').resize((32, 24), Image.BOX)).astype(float)
fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
print('参考帧 %s; 阈值 %s' % (ref, thr))
runs = []
cur = None
for f in fs:
    a = np.asarray(Image.open(os.path.join(d, f)).convert('L').resize((32, 24), Image.BOX)).astype(float)
    dmax = float(np.abs(a - r).mean())
    same = dmax <= thr
    n = int(''.join(ch for ch in f if ch.isdigit()))
    if same and cur is None:
        cur = n
    elif not same and cur is not None:
        runs.append((cur, prev))
        cur = None
    prev = n
if cur is not None:
    runs.append((cur, prev))
print('同一画面的帧区间: %s' % runs)
