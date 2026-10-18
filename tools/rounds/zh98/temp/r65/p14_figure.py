# -*- coding: utf-8 -*-
r"""p14_figure.py — 出交付用的对照图: 把实拍正文框里 O / AD / AE / B0 / B1 五行的
"字形区" 裁出来上下叠放 (放大 4 倍), 并标注每行的像素宽度。

预期: O/AD/AE/B0 四行的字形区**宽度相同 (~51px = 3 个汉字)**;
      B1 行 ~113px (6 个字形块) ⇒ 0xB1 被引擎当单字节, 每个 pair 画成两个字形。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
DUMP = os.path.join(REPO, 'work', 'builds', 'GR_TEST_PROBE_LEAD', 'temp', 'dump_probe')
SRC = os.path.join(DUMP, 'probe_page.png')
OUT = os.path.join(DUMP, 'probe_compare.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

im = Image.open(SRC).convert('RGB')
bright = np.asarray(im).mean(axis=2) > 120

# (标签, 标签字符数, 行首 x, 行墨的 y 范围)
ROWS = [
    ('O:',  2, 32, 175, 188, 'reference: live codes A6A9/A5DE/A7C2'),
    ('AD:', 3, 32, 191, 204, 'new cells 1175/1176/1177 (lead 0xAD, known good)'),
    ('AE:', 3, 32, 207, 220, 'new cells 1238/1239/1240 (lead 0xAE) -- under test'),
    ('B0:', 3, 32, 224, 236, 'new cells 1426/1427/1428 (lead 0xB0) -- under test'),
    ('B1:', 3, 32, 240, 253, 'new cells 1520/1521/1522 (lead 0xB1) -- EXPECTED DEAD'),
]
ASCII, SPACE, SC = 8, 3, 4
ZONE_W = 120
y0, y1 = 170, 260
crop = im.crop((26, y0, 32 + 30 + ZONE_W, y1))
W2, H2 = crop.width * SC, crop.height * SC
out = Image.new('RGB', (W2 + 380, H2 + 8), (0, 0, 0))
out.paste(crop.resize((W2, H2), Image.LANCZOS), (0, 4))
d = ImageDraw.Draw(out)

print('%-5s %-8s %-24s %s' % ('行', '标签宽', '字形区 x 范围', '字形区宽'))
for (lab, nch, xs, a, b, note) in ROWS:
    gx0 = xs + nch * ASCII + SPACE
    row = bright[a:b + 1, gx0:gx0 + ZONE_W]
    cols = np.where(row.any(axis=0))[0]
    goto = gx0 + (cols[-1] if len(cols) else 0)
    zw = int(cols[-1] + 1) if len(cols) else 0
    print('%-5s %-8s x=%3d..%3d            %3d px  (≈%.1f 个汉字)  %s'
          % (lab, '%d px' % (nch * ASCII + SPACE), gx0, goto, zw, zw / 16.0, note))
    yy = (a - y0) * SC + 4
    d.line([gx0 * SC, yy - 2, gx0 * SC, yy + 14 * SC], fill=(0, 255, 0), width=2)
    d.line([gx0 * SC, yy + 14 * SC, (gx0 + zw) * SC, yy + 14 * SC], fill=(255, 80, 80), width=2)
    d.text((gx0 * SC + 6, yy - 14), '%s  %d px' % (lab, zw), fill=(255, 255, 0))
    d.text((W2 + 8, yy + 8), '%s  %d px' % (lab, zw), fill=(255, 255, 0))
    d.text((W2 + 8, yy + 24), note, fill=(190, 190, 190))
out.save(OUT)
print('\n已写 %s (%dx%d)' % (OUT, out.width, out.height))
