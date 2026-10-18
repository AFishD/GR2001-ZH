# -*- coding: utf-8 -*-
r"""p07_en_atlas.py — round42: 用**正确 stride** 把 EN_ORIG 字体图集 (512x512 PSMT8) 整张导出来看
 + 检查 FT 记录矩形里的墨 (验证 UV 口径)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402
from PIL import Image                                            # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
iso = tcslib.Iso(ISO)
ft_e = pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'FONT.RES':
        ft_e = e
    elif e['name'] == 'COMMON.PAK':
        pak_e = e
    if ft_e and pak_e:
        break
ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
_head, faces = tcslib.parse_ft_faces(ft_blob)
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
nm, psm, W, HH, clut, px, OFF = [r for r in tcslib.parse_pak_records(pak)
                                 if r[0] == 'new_font_revised'][0]
print('EN_ORIG new_font_revised: %dx%d psm=0x%02X px_off=0x%X' % (W, HH, psm, OFF))


def tex(x, y):
    return pak[OFF + y * W + x]                # PSMT8 = 线性 1B/texel


buf = bytearray(W * HH)
for y in range(HH):
    for x in range(W):
        buf[y * W + x] = 0 if tex(x, y) == 0 else 255
im = Image.frombytes('L', (W, HH), bytes(buf)).convert('1', dither=Image.Dither.NONE)
im.convert('L').save(os.path.join(HERE, 'en_atlas_full.png'))
print('→ en_atlas_full.png (512x512, 黑=墨)')

print()
print('FT 记录矩形是否有墨 (口径自检):')
for fi, (fname, fld, recs) in enumerate(faces):
    print('  face %d %-8s 记录 %d' % (fi, fname, len(recs)))
for code in (0x20, 0x41, 0x61, 0xB1, 0xB5, 0xE7, 0xF1):
    idx = code - 0x20
    line = []
    for fi, (fname, fld, recs) in enumerate(faces):
        if idx >= len(recs):
            continue
        _b0, _b1, u0, v0, u1, v1 = recs[idx]
        n = sum(1 for y in range(v0, min(HH, v1)) for x in range(u0, min(W, u1))
                if tex(x, y) == 0)
        line.append('%s(%d,%d,%d,%d)墨%d' % (fname, u0, v0, u1, v1, n))
    print('  码 0x%02X (idx %3d): %s' % (code, idx, '; '.join(line)))

print()
print('引擎硬编码的文本图标 UV 框 (v=198..218) 在图集里的墨量:')
for label, (u0, v0, u1, v1) in (('0xB5 → (1,198)-(21,218)', (1, 198, 21, 218)),
                                ('0xB1 → (25,198)-(45,218)', (25, 198, 45, 218))):
    n = sum(1 for y in range(v0, v1) for x in range(u0, u1) if tex(x, y) == 0)
    print('  %-26s 墨 %d' % (label, n))

print()
print('y=198..218 这一带的**逐行**墨量 (x=0..511):')
for y in range(190, 226):
    n = sum(1 for x in range(W) if tex(x, y) == 0)
    print('  y=%3d 墨 %4d %s' % (y, n, '#' * min(60, n // 4)))
