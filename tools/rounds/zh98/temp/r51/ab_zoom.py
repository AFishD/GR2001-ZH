# -*- coding: utf-8 -*-
"""r51 证据图: 把 A/B 差异区放大对照 (上=GR_ZH98 / 下=候选盘)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont

A = sys.argv[1]
B = sys.argv[2]
frame = sys.argv[3]
out = sys.argv[4]
box = tuple(int(x) for x in sys.argv[5].split(',')) if len(sys.argv) > 5 else None
scale = int(sys.argv[6]) if len(sys.argv) > 6 else 6
pad = 26
if box is None:
    box = (250, 70, 400, 100)
x0, y0, x1, y1 = box
x0 -= pad
x1 += pad
y0 -= 6
y1 += 6
ia = Image.open(os.path.join(A, frame)).convert('RGB').crop((x0, y0, x1, y1))
ib = Image.open(os.path.join(B, frame)).convert('RGB').crop((x0, y0, x1, y1))
w, h = ia.size
im = Image.new('RGB', (w * scale, h * scale * 2 + 46), (255, 255, 255))
im.paste(ia.resize((w * scale, h * scale), Image.NEAREST), (0, 20))
im.paste(ib.resize((w * scale, h * scale), Image.NEAREST), (0, h * scale + 40))
d = ImageDraw.Draw(im)
f = ImageFont.load_default()
try:
    from PIL import ImageFont as IF
    f = IF.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '..', '..', '..', '..', 'third_party', 'fonts',
                                 '方正像素16.ttf'), 15)
except Exception:                                                         # noqa: BLE001
    pass
d.text((4, 3), 'A = GR_ZH98 (before)   title bar @ %s' % frame, fill=(0, 0, 0), font=f)
d.text((4, h * scale + 24), 'B = fixed build (after)', fill=(0, 0, 0), font=f)
im.save(out)
print('-> %s  %s' % (out, im.size))
