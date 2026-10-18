# -*- coding: utf-8 -*-
r"""p20_atlas_cmp.py — 出「重排前 / 重排后」图集对照图 (给报告用, 2 倍最近邻)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
from PIL import Image, ImageDraw                                # noqa: E402

A = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'font', 'GR_ZH94_font_atlas.png')
B = os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'font', 'GR_ZH95_font_atlas.png')
ia = Image.open(A).convert('RGB')
ib = Image.open(B).convert('RGB')
print('A %s  B %s' % (ia.size, ib.size))
w, h = ia.size
gap, bar = 8, 24
out = Image.new('RGB', (w, h * 2 + gap + bar * 2), (255, 255, 255))
d = ImageDraw.Draw(out)
out.paste(ia, (0, bar))
d.text((6, 6), 'BEFORE  GR_ZH94  (used 1319, blank-usable 42)', fill=(180, 0, 0))
out.paste(ib, (0, bar * 2 + h + gap))
d.text((6, bar * 2 + h + gap + 6), 'AFTER   GR_ZH95  (used 1319, blank-usable 90)', fill=(0, 110, 0))
op = os.path.join(REPO, 'docs', 'img')
os.makedirs(op, exist_ok=True)
p = os.path.join(op, 'r46_atlas_before_after.png')
out.save(p, optimize=True)
print('->', p, out.size)

# 再出一张「轴区放大」: 行 11/18/19/21..24 那一片 (y 170..460, x 0..1024) 的前后对照
crop = (0, 170, 1024, 460)
ca, cb = ia.crop(crop), ib.crop(crop)
cw, ch = ca.size
out2 = Image.new('RGB', (cw, ch * 2 + gap + bar * 2), (255, 255, 255))
d2 = ImageDraw.Draw(out2)
out2.paste(ca, (0, bar))
d2.text((6, 6), 'BEFORE  rows 11..24 (blank cells scattered, stale ink)', fill=(180, 0, 0))
out2.paste(cb, (0, bar * 2 + ch + gap))
d2.text((6, bar * 2 + ch + gap + 6), 'AFTER   glyphs packed to the front, rest zeroed', fill=(0, 110, 0))
p2 = os.path.join(op, 'r46_atlas_zoom_before_after.png')
out2.save(p2, optimize=True)
print('->', p2, out2.size)
