# -*- coding: utf-8 -*-
r"""sampled_legend.py — 裁 sampled 图的一小块, 看清红/蓝标记各代表什么"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font',
                 'GR_ZH93_font_atlas_sampled.png')
OUT = os.path.join(HERE, 'sampled_crop.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

im = Image.open(P).convert('RGB')
w, h = im.size
print('sampled 图 %dx%d' % (w, h))
# 取色统计
from collections import Counter
c = Counter(im.getdata())
print('颜色 top 6:', c.most_common(6))
# 红/蓝像素位置
px = im.load()
reds = [(x, y) for y in range(0, min(h, 200)) for x in range(0, min(w, 300))
        if px[x, y][0] > 200 and px[x, y][1] < 230 and px[x, y][2] < 230]
blues = [(x, y) for y in range(0, min(h, 200)) for x in range(0, min(w, 300))
         if px[x, y][2] > 200 and px[x, y][0] < 200]
print('淡红像素 %d, 淡蓝像素 %d' % (len(reds), len(blues)))
if blues:
    print('  蓝色样本点:', blues[:6])
    print('  蓝色的 x 分布 (前 20 个不同值):', sorted({x for x, _ in blues})[:20])
if reds:
    print('  红色的 x 分布 (前 20 个不同值):', sorted({x for x, _ in reds})[:20])
crop = im.crop((0, 0, 200, 80)).resize((200 * 4, 80 * 4), Image.NEAREST)
crop.save(OUT)
print('裁图 →', os.path.relpath(OUT, REPO))
