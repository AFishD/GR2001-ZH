# -*- coding: utf-8 -*-
r"""v9_crop.py — round47 出图: 「中/斗」记录格 y=353 那一行 修前/修后 对比图 (给报告用)。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw                                          # noqa: E402
from r47lib import load                                                   # noqa: E402

BOX = (880, 320, 1000, 372)          # 「以到中定斗是任」这一段的记录格 (行 18) + 下面一行
outs = []
for ver in ('GR_ZH94', 'GR_ZH96_fix'):
    eng = load(ver)['eng']
    im = Image.new('L', (BOX[2] - BOX[0], BOX[3] - BOX[1]), 255)
    px = im.load()
    for y in range(BOX[1], BOX[3]):
        for x in range(BOX[0], BOX[2]):
            px[x - BOX[0], y - BOX[1]] = 0 if eng[y, x] else 255
    z = 7
    im = im.resize((im.width * z, im.height * z), Image.NEAREST).convert('RGB')
    d = ImageDraw.Draw(im)
    # 标出记录格边界 (16px 网格) 与"溢出带行" y=353
    for x in range(BOX[0], BOX[2], 16):
        d.line([( (x - BOX[0]) * z, 0), ((x - BOX[0]) * z, im.height)], fill=(220, 220, 255))
    for y in (338, 354, 370):
        if BOX[1] <= y < BOX[3]:
            d.line([(0, (y - BOX[1]) * z), (im.width, (y - BOX[1]) * z)], fill=(255, 200, 200))
    for y in (353,):
        d.line([(0, (y - BOX[1]) * z), (im.width, (y - BOX[1]) * z)], fill=(255, 80, 80))
        d.line([(0, (y - BOX[1]) * z + z - 1), (im.width, (y - BOX[1]) * z + z - 1)], fill=(255, 80, 80))
    p = os.path.join(HERE, 'crop_%s.png' % ver)
    im.save(p)
    outs.append(p)
    print('→ %s (%dx%d)' % (p, im.width, im.height))

# 拼一张上下对比
a, b = Image.open(outs[0]), Image.open(outs[1])
c = Image.new('RGB', (a.width, a.height * 2 + 12), (255, 255, 255))
c.paste(a, (0, 0))
c.paste(b, (0, a.height + 12))
p = os.path.join(HERE, 'crop_band_ab.png')
c.save(p)
print('→ %s' % p)
