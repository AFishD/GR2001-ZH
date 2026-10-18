# -*- coding: utf-8 -*-
"""_probe_snap.py -- 看抓帧尺寸与几帧的墨分布概况 (只读, 轻量)。"""
import os
import sys

from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

d = sys.argv[1]
fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
print('dir=%s  frames=%d' % (d, len(fs)))
for f in fs[:3] + fs[-3:]:
    im = Image.open(os.path.join(d, f))
    print('  %s  %s %s' % (f, im.size, im.mode))
