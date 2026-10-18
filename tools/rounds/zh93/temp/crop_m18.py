# -*- coding: utf-8 -*-
r"""crop_m18.py — 从实机帧裁出 M18 介绍框并放大, 便于核对译文与断行"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'dump_WEAPONS2',
                   'snap_f00022700.png')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'M18_译文_实机_GR_ZH93.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

im = Image.open(SRC).convert('RGB')
w, h = im.size
print('原帧 %dx%d' % (w, h))
# 介绍框大致范围 (按 583x437 观察: x 20..250, y 140..340)
box = (18, 140, 252, 340)
crop = im.crop(box)
scale = 3
crop = crop.resize((crop.width * scale, crop.height * scale), Image.NEAREST)
crop.save(OUT)
print('已存 %s  (%dx%d, %d 倍最近邻)' % (os.path.relpath(OUT, REPO), crop.width, crop.height, scale))
