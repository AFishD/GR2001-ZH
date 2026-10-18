# -*- coding: utf-8 -*-
r"""m12_ftq.py — 查: 谁会采样 (128,385)/(128,370) 一带? 即哪些 FT 记录框覆盖这些坐标。
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
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        PX = off
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
INK = (A == 0)

TARGETS = [(128, 370), (128, 386), (736, 370), (736, 386), (32, 386), (992, 370)]
for (tx, ty) in TARGETS:
    print('== 采样窗 (%d,%d) 附近: 谁的记录框覆盖它? ==' % (tx, ty))
    hits = []
    for fname in ('large', 'default', 'huge'):
        for code, rec in enumerate(faces[[f[0] for f in faces].index(fname)][2]):
            _b0, _b1, u0, v0, u1, v1 = rec
            if u1 <= u0 or v1 <= v0:
                continue
            if u0 <= tx < u1 and v0 <= ty < v1:
                hits.append(('rec', fname, code + 0x20, u0, v0, u1, v1))
            sx, sy = (u0 + 576) % W, v0 + 1
            if sx <= tx < sx + 16 and sy <= ty < sy + 16:
                hits.append(('eng', fname, code + 0x20, sx, sy, sx + 16, sy + 16))
    if not hits:
        print('   (无记录框覆盖 —— 该像素不被任何 FT 采样点读到)')
    for h in hits[:12]:
        print('   %s %-8s code=0x%02X box=(%d,%d,%d,%d)' % h)
    # 该坐标周围 24x24 的墨
    y0, x0 = ty, tx
    print('   周围墨 (y=%d..%d, x=%d..%d):' % (y0 - 2, y0 + 18, x0 - 2, x0 + 18))
    for yy in range(y0 - 2, y0 + 19):
        print('     %s' % ''.join('#' if INK[yy, xxx] else '.' for xxx in range(x0 - 2, x0 + 19)))
    print()
