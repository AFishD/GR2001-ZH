# -*- coding: utf-8 -*-
r"""m10_ascii.py — 用 ASCII 图打印 17 个拟用落点 (含 2px 上下文) 的墨迹, 便于逐格确认。
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
PICK = [1246, 1245, 1284, 1278, 1302, 1300, 1277, 1286, 1301, 1289, 1290, 1298, 1299, 1294,
        1296, 1308, 1280]
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


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


for s in PICK:
    R, C = s // 62, s % 62
    x, y = 16 * ((C + 2) % 64), yrow(R)
    xt = 4 + 16 * C
    print('== slot %4d 码 %02X%02X  行 %d  C=%d' % (s, 0xA1 + s // 94, 0xA1 + s % 94, R, C))
    for tag, xx in (('引擎格', x), ('tcs 格', xt)):
        print('   %s (%d,%d) 墨=%d' % (tag, xx, y, int(INK[y:y + 16, xx:xx + 16].sum())))
        for yy in range(y - 2, y + 18):
            line = ''.join('#' if INK[yy, xxx] else '.' for xxx in range(xx - 2, xx + 18))
            marker = '|' + ('' if yy < y or yy >= y + 16 else '')
            print('     %s   y=%d %s' % (line, yy, marker))
    print()
