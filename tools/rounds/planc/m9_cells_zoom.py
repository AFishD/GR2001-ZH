# -*- coding: utf-8 -*-
r"""m9_cells_zoom.py — 把 17 个拟用落点 (引擎格 + tcslib 格) 放大拼图, 目视确认格子里是什么。
产物: work/_planc/cells_zoom.png
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw                        # noqa: E402
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
W, H, CW, CH = 1024, 512, 16, 16
PICK = [1246, 1245, 1284, 1278, 1302, 1300, 1277, 1286, 1301, 1289, 1290, 1298, 1299, 1294,
        1296, 1308, 1280]
Z = 4

iso = tcslib.Iso(BASE)
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        PX = off
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
img = np.where(A == 0, 0, 255).astype(np.uint8)


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


PAD = 26
tile = (CW + 2) * Z
cols = 3
rows_n = len(PICK)
im = Image.new('RGB', (cols * (tile + 8) + 8, rows_n * (tile + PAD) + 8), (245, 245, 245))
d = ImageDraw.Draw(im)
for i, s in enumerate(PICK):
    R, C = s // 62, s % 62
    x = 16 * ((C + 2) % 64)
    y = yrow(R)
    xt = 4 + 16 * C
    cy, cx = divmod(i, cols)
    ox = 8 + cx * (tile + 8)
    oy = 8 + cy * (tile + PAD)
    for j, (xx, tag) in enumerate(((x, 'eng'), (xt, 'tcs'))):
        crop = img[y - 1:y + CH + 1, max(0, xx - 1):xx + CW + 1]
        cim = Image.fromarray(crop).convert('RGB').resize(
            ((crop.shape[1]) * Z, (crop.shape[0]) * Z), Image.NEAREST)
        px0 = ox + j * (tile + 4)
        im.paste(cim, (px0, oy + 14))
        d.rectangle([px0 + Z, oy + 14 + Z, px0 + Z + CW * Z, oy + 14 + Z + CH * Z],
                    outline=(255, 0, 0) if j == 0 else (0, 150, 0), width=1)
        d.text((px0, oy), '%02X%02X %s (%d,%d)' % (0xA1 + s // 94, 0xA1 + s % 94, tag, xx, y),
               fill=(0, 0, 0))
p = os.path.join(HERE, 'cells_zoom.png')
im.save(p)
print('-> %s %s' % (p, im.size))
