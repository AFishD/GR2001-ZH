# -*- coding: utf-8 -*-
r"""m16_single_geom.py — 单字节码的字形几何: 记录框 vs 引擎采样框, 谁真的在盘上有墨、多高多宽。
这决定"我写行20的格子会不会切到 0xDD..0xFE 这些常用字的底部 1px"。
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
ft_e = pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
    elif e['name'] == 'FONT.RES':
        ft_e = e
ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
_he, faces = tcslib.parse_ft_faces(ft_blob)
FI = {f[0]: i for i, f in enumerate(faces)}
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        PX = off
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
INK = (A == 0)


def bbox(x0, y0, w=16, h=18):
    sub = INK[y0:y0 + h, x0:x0 + w]
    ys, xs = np.where(sub)
    if not len(ys):
        return None
    return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max(), len(ys))


print('码   大字面记录 (u0,v0,u1,v1)      记录框墨  引擎框(u0+576,v0+1) 墨  bbox')
for code in (0xC9, 0xDD, 0xDE, 0xE0, 0xE5, 0xF0, 0xF7, 0xFE, 0xAF, 0xB4):
    rec = faces[FI['default']][2][code - 0x20]
    _b0, _b1, u0, v0, u1, v1 = rec
    r_ink = int(INK[v0:v0 + 16, u0:u0 + 16].sum())
    ex, ey = (u0 + 576) % W, v0 + 1
    e_ink = int(INK[ey:ey + 16, ex:ex + 16].sum())
    bb = bbox(ex, ey)
    print('0x%02X rec=(%4d,%3d,%4d,%3d)  %5d     eng=(%4d,%3d)      %5d  %s'
          % (code, u0, v0, u1, v1, r_ink, ex, ey, e_ink, bb))

print()
print('== 行19 单字节字形的墨高 (y=352..372, x=608..624 / 624..640 ...) ==')
for k in range(6):
    x = 608 + 16 * k
    ys, xs = np.where(INK[350:374, x:x + 16])
    if len(ys):
        print('  x=%4d: 墨 y=%d..%d (高 %d), 墨量 %d'
              % (x, 350 + ys.min(), 350 + ys.max(), ys.max() - ys.min() + 1, len(ys)))
    else:
        print('  x=%4d: 无墨' % x)
