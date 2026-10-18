# -*- coding: utf-8 -*-
r"""m7_visual.py — 把基盘图集的下半区 (行 18..27) 放大成 PNG, 画 16px 网格 + 候选格标记,
以便**用眼睛**确认候选格里那些零星墨点到底是什么。

只读基盘, 产物写到 work/_planc/ (不碰 GR_ZH93/temp)。
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
CS = tcslib.CHARSET
W, H = 1024, 512
Z = 2

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
img = np.where(A == 0, 0, 255).astype(np.uint8)      # 墨=黑

js = json.load(open(CS, encoding='utf-8'))
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
used = {(b0 - 0xA1) * 94 + (b1 - 0xA1) for (b0, b1) in pair_of.values()}


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


def dump(y0, y1, name, marks):
    crop = img[y0:y1]
    im = Image.fromarray(crop).convert('RGB').resize(((y1 - y0) and (W * Z), (y1 - y0) * Z),
                                                     Image.NEAREST)
    d = ImageDraw.Draw(im)
    for r in range(0, 32):
        yy = yrow(r)
        if y0 <= yy < y1:
            d.line([(0, (yy - y0) * Z), (W * Z, (yy - y0) * Z)], fill=(0, 160, 255), width=1)
            d.text((2, (yy - y0) * Z + 2), 'R%d y=%d' % (r, yy), fill=(255, 0, 0))
    for k in range(65):
        d.line([(k * 16 * Z, 0), (k * 16 * Z, (y1 - y0) * Z)], fill=(220, 220, 220), width=1)
    for (x, y, col, tag) in marks:
        if y0 <= y < y1:
            d.rectangle([x * Z, (y - y0) * Z, (x + 16) * Z - 1, (y - y0 + 16) * Z - 1],
                        outline=col, width=2)
            d.text((x * Z + 2, (y - y0) * Z + 14), tag, fill=col)
    p = os.path.join(HERE, name)
    im.save(p)
    print('-> %s  (%dx%d)' % (p, im.size[0], im.size[1]))


marks = []
# 候选: 行20 (lead 0xAE 空闲槽)
for s in range(1222, 1316):
    if s in used:
        continue
    R, C = s // 62, s % 62
    if R != 20:
        continue
    x = 16 * ((C + 2) % 64)
    marks.append((x, yrow(20), (255, 0, 0), '%02X%02X' % (0xA1 + s // 94, 0xA1 + s % 94)))
    marks.append((4 + 16 * C, yrow(20), (0, 170, 0), ''))
dump(338, 434, 'atlas_r19_r23.png', marks)

# 全下半区 (行 22..27), 无标记
dump(402, 512, 'atlas_r22_r27.png', [])
