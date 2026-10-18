# -*- coding: utf-8 -*-
r"""p6_expected.py — 探针盘的"预期图": 把探针盘上**新格里的字形**逐个渲染出来,
再和"对照组 (现役格)"并排, 供实拍后逐字比对。

输出 p6_expected.png:
  第一行 = 对照 (现役码位) 我 国 山
  第二行 = AD 新格 / AE 新格 / B0 新格 / B1 新格  —— 每格一个方块 (放大 10 倍)
另外把 FT 记录里 0xB1/0xB2/0xB5 的采样窗也渲染出来 (S: 那一行的预期)。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                     # noqa: E402
import tcslib                                                             # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_TEST_PROBE_LEAD', 'GR_TEST_PROBE_LEAD.iso')
OUT = os.path.join(HERE, 'p6_expected.png')
f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)

SC = 10
ITEMS = [
    ('O 我', 'pair', 0xA6, 0xA9), ('O 国', 'pair', 0xA5, 0xDE), ('O 山', 'pair', 0xA7, 0xC2),
    ('AD 我', 'pair', 0xAD, 0xD0), ('AD 国', 'pair', 0xAD, 0xD1), ('AD 山', 'pair', 0xAD, 0xD2),
    ('AE 我', 'pair', 0xAE, 0xB1), ('AE 国', 'pair', 0xAE, 0xB2), ('AE 山', 'pair', 0xAE, 0xB3),
    ('B0 我', 'pair', 0xB0, 0xB1), ('B0 国', 'pair', 0xB0, 0xB2), ('B0 山', 'pair', 0xB0, 0xB3),
    ('B1 我', 'pair', 0xB1, 0xB1), ('B1 国', 'pair', 0xB1, 0xB2), ('B1 山', 'pair', 0xB1, 0xB3),
    ('S 0xB2', 'ft', 0xB2), ('S 0xB1', 'ft', 0xB1), ('S 0xB5', 'ft', 0xB5),
]
cell = 16 * SC
img = Image.new('RGB', (len(ITEMS) * (cell + 6) + 6, cell + 120), (255, 255, 255))
d = ImageDraw.Draw(img)
fdef = [x for x in faces if x[0] == 'default'][0][2]

for i, it in enumerate(ITEMS):
    ox = 6 + i * (cell + 6)
    oy = 60
    if it[1] == 'pair':
        slot = tcslib.pair_slot(it[2], it[3])
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        sub = gray[y:y + 16, x:x + 16]
        d.text((ox, 4), it[0], fill=(0, 0, 0))
        d.text((ox, 18), '%02X%02X' % (it[2], it[3]), fill=(0, 0, 160))
        d.text((ox, 32), 'row%d c%d' % (slot // 62, slot % 62), fill=(120, 120, 120))
        print('%-7s pair %02X%02X slot=%4d row=%2d col=%2d cell=(%4d,%3d) 墨=%d'
              % (it[0], it[2], it[3], slot, slot // 62, slot % 62, x, y, int((sub == 0).sum())))
    else:
        idx = it[2] - 0x20
        _b0, _b1, u0, v0, u1, v1 = fdef[idx]
        sub = np.full((16, 16), 255, dtype=np.uint8)
        if u1 > u0 and v1 > v0:
            hh, ww = min(16, v1 - v0), min(16, u1 - u0)
            sub[:hh, :ww] = gray[v0:v0 + hh, u0:u0 + ww]
        d.text((ox, 4), it[0], fill=(0, 0, 0))
        d.text((ox, 18), 'rec%d' % idx, fill=(0, 0, 160))
        d.text((ox, 32), '%d,%d' % (u0, v0), fill=(120, 120, 120))
        print('%-7s FT rec[%d] (%d,%d,%d,%d) 墨=%d' % (it[0], idx, u0, v0, u1, v1,
                                                       int((sub == 0).sum())))
    for yy in range(16):
        for xx in range(16):
            if sub[yy, xx] == 0:
                d.rectangle([ox + xx * SC, oy + yy * SC,
                             ox + (xx + 1) * SC - 1, oy + (yy + 1) * SC - 1], fill=(0, 0, 0))
    d.rectangle([ox, oy, ox + cell - 1, oy + cell - 1], outline=(255, 0, 0))
    if i in (2, 5, 8, 11, 14):
        d.line([ox + cell + 3, 0, ox + cell + 3, cell + 120], fill=(0, 160, 0), width=2)
img.save(OUT)
print('\n已写 %s' % OUT)
