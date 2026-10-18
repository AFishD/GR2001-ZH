# -*- coding: utf-8 -*-
r"""r47lib.py — round47 共用：读任一盘的「引擎口径图集」+ FT 记录表 (只读)。

引擎口径 = 按 GIF 封包分段把每段 payload 放到 TRXPOS 指定的行 (与 patch_zh94_glyph_align.Atlas 同一口径)。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import patch_zh94_glyph_align as P                     # noqa: E402

W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH


def yrow(r):
    return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def iso_path(ver):
    return os.path.join(REPO, 'work', 'builds', ver, ver + '.iso')


def load(ver, want_ft=True):
    """返回 dict(ver, pak, PX, px_size, A(Atlas), faces, rects, by_rec_idx)."""
    p = iso_path(ver)
    assert os.path.isfile(p), p
    iso = tcslib.Iso(p)
    pak_e = ft_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
        elif e['name'] == 'FONT.RES':
            ft_e = e
        if pak_e and ft_e:
            break
    assert pak_e and ft_e, (ver, pak_e, ft_e)
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    out = dict(ver=ver, iso=p, pak_e=pak_e, ft_e=ft_e)
    if want_ft:
        ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
        out['ft_blob'] = ft_blob
        _he, faces = tcslib.parse_ft_faces(ft_blob)
        out['faces'] = faces
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised']
    assert len(rec) == 1, (ver, [r[0] for r in tcslib.parse_pak_records(bytes(pak))])
    _nm, psm, w, h, clut, px_size, PX = rec[0]
    assert (psm, w, h) == (0x14, W, H), (psm, w, h)
    out.update(PX=PX, px_size=px_size, psm=psm, clut=clut)
    A = P.Atlas(pak, PX, px_size)
    out['A'] = A
    out['eng'] = A.eng
    out['cov'] = A.cov
    out['segs'] = A.segs
    return out


def rects_all(faces):
    """[(face, code, u0, v0, u1, v1)] —— 3 个 face 的全部记录矩形。"""
    out = []
    for fname, _fld, rs in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            out.append((fname, idx + 0x20, u0, v0, u1, v1))
    return out


def default_rects(faces):
    """default face 的记录矩形 (引擎实际用的那张表) → {code: (u0,v0,u1,v1)}"""
    fi = {f[0]: f[2] for f in faces}
    out = {}
    for idx, r in enumerate(fi['default']):
        _b0, _b1, u0, v0, u1, v1 = r
        out[idx + 0x20] = (u0, v0, u1, v1)
    return out


def ascii_dump(img, x0, x1, y0, y1, mark='#'):
    """把图集的一块打成 ASCII (行首带 y)。"""
    lines = []
    for y in range(y0, y1):
        lines.append('%4d |%s|' % (y, ''.join(mark if img[y, x] else '.'
                                              for x in range(x0, x1))))
    return lines
