# -*- coding: utf-8 -*-
r"""p04_icon_band.py — round42: 把字库图集里的「图标条」抠出来看 (只读)

引擎里两个**文本图标码**的硬编码 UV (ELF DrawString v1 @0x219C08..0x219C8C):
    0xB5 → (u 1..21, v 198..218)
    0xB1 → (u 25..45, v 198..218)
kShortcutDefaultTC (@0x2BEFE0) 里另有一批 20x20 图标:
    26 → (0,178)-(20,198)   27 → (85,178)-(120,198)  28 → (0,178)-(20,198)
    29 → (21,178)-(41,198)  30 → (42,178)-(62,198)   31 → (63,178)-(83,198)
⇒ 图集 y≈170..220 这一带就是「手柄按键图标条」。本脚本把它抠成 PNG 给人看,
  并列出候选码位 (0xB1/0xB5/0xE7/0xF1) 在 FT 记录表里的矩形与有没有墨。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                    # noqa: E402
from PIL import Image                                            # noqa: E402

OUT = HERE
ISOS = [('EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')),
        ('ZH93', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))]
BAND = (0, 168, 260, 224)          # x0,y0,x1,y1


def load_atlas(iso_path):
    iso = tcslib.Iso(iso_path)
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
    _he, faces = tcslib.parse_ft_faces(ft_blob)
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    atlas = None
    for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
        if nm == 'new_font_revised':
            atlas = dict(pak=pak, off=off, w=w, h=h)
            break
    iso.close()
    return faces, atlas


def gray(atlas):
    pak, off, w, h = atlas['pak'], atlas['off'], atlas['w'], atlas['h']
    stride = w // 2
    LON = bytes(i & 0xF for i in range(256))
    HIN = bytes((i >> 4) & 0xF for i in range(256))
    INK = bytes(0 if i == 0 else 255 for i in range(256))
    buf = bytearray(w * h)
    for y in range(h):
        row = pak[off + y * stride: off + (y + 1) * stride]
        buf[y * w: y * w + w: 2] = row.translate(LON).translate(INK)
        buf[y * w + 1: y * w + w: 2] = row.translate(HIN).translate(INK)
    return bytes(buf)


for tag, iso in ISOS:
    if not os.path.isfile(iso):
        print('[skip] %s 不存在' % iso)
        continue
    faces, atlas = load_atlas(iso)
    g = gray(atlas)
    w, h = atlas['w'], atlas['h']
    # ① 抠图标条 (放大 6 倍, 最近邻)
    x0, y0, x1, y1 = BAND
    im = Image.frombytes('L', (w, h), g).crop((x0, y0, x1, y1))
    im = im.convert('1', dither=Image.Dither.NONE).convert('L')
    big = im.resize(((x1 - x0) * 6, (y1 - y0) * 6), Image.NEAREST)
    p = os.path.join(OUT, 'icon_band_%s.png' % tag)
    big.save(p)
    print('=' * 78)
    print('%s: 图集 %dx%d, 图标条 y=%d..%d, x=%d..%d (放大 6 倍) → %s'
          % (tag, w, h, y0, y1, x0, x1, os.path.basename(p)))
    print('=' * 78)
    # ② 逐格列墨量 (20x20 网格, 从 x=0 起每 1px 步进太重 ⇒ 按 6px 粗扫)
    print('   该带内「有墨的列区间」:')
    runs, cur = [], None
    for x in range(x0, x1):
        col_ink = any(g[y * w + x] == 0 for y in range(y0, y1))
        if col_ink and cur is None:
            cur = x
        elif not col_ink and cur is not None:
            runs.append((cur, x)); cur = None
    if cur is not None:
        runs.append((cur, x1))
    print('     %s' % (' '.join('%d..%d' % r for r in runs) or '全空'))
    # ③ 候选码位的 FT 记录
    print('   候选码位的 FT 记录 (face large/default/huge; idx = 码位-0x20):')
    for b in (0xB1, 0xB5, 0xE7, 0xF1):
        idx = b - 0x20
        cell = []
        for fi, (nm, fld, recs) in enumerate(faces):
            if idx < len(recs):
                _b0, _b1, u0, v0, u1, v1 = recs[idx]
                ink = 0
                for y in range(v0, min(h, v1)):
                    for x in range(u0, min(w, u1)):
                        if g[y * w + x] == 0:
                            ink += 1
                cell.append('%s(%d,%d,%d,%d)墨%d' % (nm, u0, v0, u1, v1, ink))
        print('     0x%02X (idx %d): %s' % (b, idx, '; '.join(cell)))
    # ④ 硬编码 UV 处到底有没有墨
    print('   引擎硬编码 UV 处的墨点数:')
    for label, (u0, v0, u1, v1) in (('0xB5 → text icon', (1, 198, 21, 218)),
                                    ('0xB1 → text icon', (25, 198, 45, 218)),
                                    ('shortcut 26/28', (0, 178, 20, 198)),
                                    ('shortcut 29', (21, 178, 41, 198)),
                                    ('shortcut 30', (42, 178, 62, 198)),
                                    ('shortcut 31', (63, 178, 83, 198)),
                                    ('shortcut 27', (85, 178, 120, 198))):
        n = sum(1 for y in range(v0, v1) for x in range(u0, u1) if g[y * w + x] == 0)
        print('     %-18s (%3d,%3d)-(%3d,%3d): 墨 %d' % (label, u0, v0, u1, v1, n))
    print()
