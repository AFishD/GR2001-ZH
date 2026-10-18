# -*- coding: utf-8 -*-
r"""atlas_artifact.py — 逐行找伪影: 左边界 (x<4) 有墨 = 伪影; 另看每 4 行的模式"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font', 'GR_ZH93_font_atlas_1x.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

im = Image.open(P).convert('L')
w, h = im.size
px = im.load()

print('图集 %dx%d ; 左边界 x<4 应当全空 (ATLAS_X0=4)' % (w, h))
bad = []
for y in range(h):
    n = sum(1 for x in range(4) if px[x, y] < 128)
    if n:
        bad.append((y, n))
print('左边界有墨的行: %d 行' % len(bad))
print('  %s' % ', '.join('y=%d(%dpx)' % (y, n) for y, n in bad[:30]))
if len(bad) > 30:
    print('  … 共 %d 行' % len(bad))
print()
# 行号 mod 4 / mod 16 分布
import collections
c4 = collections.Counter(y % 4 for y, _ in bad)
c16 = collections.Counter(y % 16 for y, _ in bad)
print('mod 4 分布:', dict(sorted(c4.items())))
print('mod 16 分布:', dict(sorted(c16.items())))
print()
print('前 8 行 x<4 的像素:')
for y in range(8):
    print('  y=%2d  %s' % (y, ''.join('X' if px[x, y] < 128 else '.' for x in range(12))))
print()
print('y=0 整行墨点位置 (前 40 个):')
pos = [x for x in range(w) if px[x, 0] < 128]
print('  count=%d  前40: %s' % (len(pos), pos[:40]))
print()
# 检查图集数据本身: 第 0 行 (512 字节) 的前 16 字节 vs 第 1 行
print('★ 图集原始数据对照 (需要 tcslib 解包) —— 见下一步脚本')
