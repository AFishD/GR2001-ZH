# -*- coding: utf-8 -*-
r"""inspect_atlas.py — 看 dump 出的图集有没有伪影 (用户报: 左上角一行不连续像素, 此后每隔4行一次)"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font', 'GR_ZH93_font_atlas_1x.png')
OUT = os.path.join(HERE, 'atlas_top.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

im = Image.open(P).convert('L')
w, h = im.size
print('图集 %dx%d' % (w, h))
px = im.load()

# 统计每行的墨点数, 找出异常行
print('\n每行墨点数 (前 40 行):')
for y in range(min(40, h)):
    n = sum(1 for x in range(w) if px[x, y] < 128)
    mark = '  ← 异常?' if 0 < n < 5 else ''
    print('  y=%3d  墨 %5d%s' % (y, n, mark))

print('\n前 4 行的最左 40 像素 (X=墨, .=空):')
for y in range(4):
    print('  y=%d  %s' % (y, ''.join('X' if px[x, y] < 128 else '.' for x in range(40))))

# 放大左上角
crop = im.crop((0, 0, 200, 40)).resize((200 * 4, 40 * 4), Image.NEAREST)
crop.save(OUT)
print('\n已存放大图 (左上 200x40, 4 倍):', os.path.relpath(OUT, REPO))
