# -*- coding: utf-8 -*-
r"""m11_band.py — 打印 行19..21 带 (y=350..406) 在 x=88..200 的 ASCII 墨图, 看清各带的真实排布。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
W, H = 1024, 512
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
INK = (A == 0)

X0, X1 = 88, 216
for y in range(348, 408):
    line = ''.join('#' if INK[y, x] else ('.' if (x % 16) else ':') for x in range(X0, X1))
    print('%3d %s' % (y, line))
print('    ' + ''.join(('|' if (x % 16) == 0 else ' ') for x in range(X0, X1)))
print('    x = %s' % ' '.join('%d' % x for x in range(X0, X1, 16)))
