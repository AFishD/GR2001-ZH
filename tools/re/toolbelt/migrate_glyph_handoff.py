# -*- coding: utf-8 -*-
r"""migrate_glyph_handoff.py — 给借槽字**导出字形与落格坐标** (只读, 不动盘)

    python tools/re/toolbelt/migrate_glyph_handoff.py <src.iso> [--out DIR] [--gate 0xBA]
                                              [--ncol 64] [--h 644]

为什么需要: 迁移把 `0xB5(✕图标)/0xB6(击)/0xB7(小)/0xB8(时)/0xB9(按)` 从**单字节码**改成了
**对偶码** (借槽 slot 2345..2349)。单字节码的字形走 FONT.RES 的**记录矩形** (记录索引 =
码 − 0x20); 对偶码走**图集格** (slot → row/col → cell) ⇒ 必须有人在新槽位上画一份同样的字形。

本工具把"现役盘上那 5 个字现在长什么样、在记录的哪个矩形里"**原样导出** (16×16 位图 +
PNG + 落格坐标), 交给几何路 (geom2400) 直接 blit —— 这样借槽的字**不是空白**, 而是原字形。
★ 本工具**只读**: 不写 ISO、不写 PAK、不写 FONT.RES、不写 charset。
"""
import argparse
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402

# 借槽字: 单字节码 → (字, 借到的 slot)   (借条见 work/builds/GR_TXMIG/migration_pairs.json)
BORROW = {0xB5: ('\ue0b5', 2349), 0xB6: ('\u51fb', 2348), 0xB7: ('\u5c0f', 2347),
          0xB8: ('\u65f6', 2346), 0xB9: ('\u6309', 2345)}
REC_BASE = 0x20          # FONT.RES 记录索引 = 单字节码 − face[+0x20] = code − 0x20
W_DEFAULT = 16


def cell_xy(slot, ncol, h, skip_rows=3, y0=2, ch=16):
    """几何路 (geom2400) 的引擎格公式: row=slot/ncol, col=slot%ncol, y=2+16*(row+3)。"""
    row, col = slot // ncol, slot % ncol
    return 16 * col, y0 + ch * (row + skip_rows), row, col


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('iso')
    ap.add_argument('--out', default=None)
    ap.add_argument('--gate', default='0xBA')
    ap.add_argument('--ncol', type=int, default=64, help='几何路计划改成的列数 (默认 64)')
    ap.add_argument('--h', type=int, default=644, help='几何路计划的图集高 (默认 644)')
    a = ap.parse_args(argv)
    gate = int(a.gate, 16)
    out = os.path.abspath(a.out or os.path.join(REPO, 'work', 'builds', 'GR_TXMIG',
                                                'temp', 'handoff'))
    os.makedirs(out, exist_ok=True)
    iso = T.Iso(a.iso)

    # ── FONT.RES (default face) ──
    ft_e = pak_e = None
    for i in range(64):
        e = iso.img_entry(T.MENU_LBA, i)
        if e['name'] == 'FONT.RES':
            ft_e = e
        elif e['name'] == 'COMMON.PAK':
            pak_e = e
        if ft_e and pak_e:
            break
    ft = b''.join(s[0] for s in T.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    _end, faces = T.parse_ft_faces(ft)
    names = [f[0] for f in faces]
    fi = T.FONT_FACE_DEFAULT
    recs = faces[fi][2]
    print('[ft ] faces=%s ; 用 face=%r ; nrec=%d' % (names, names[fi], len(recs)))

    # ── 图集 (COMMON.PAK new_font_revised) ──
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    atl = None
    for (nm, psm, w, h, clut, px, off) in T.parse_pak_records(pak):
        if nm == 'new_font_revised':
            atl = (pak, off, w, h, psm, clut)
            break
    assert atl, 'COMMON.PAK 里找不到 new_font_revised'
    (pakb, px_off, AW, AH, psm, clut) = atl
    segs = T.atlas_container_segments(pakb[px_off:px_off + AW * AH // 2 + 16], AW // 2)
    print('[pak] new_font_revised %dx%d psm=0x%02X clut=%d ; GIF 段 %s'
          % (AW, AH, psm, clut, segs))


    def nib(x, y):
        """引擎口径取 texel (按 GIF 封包行映射): 返回 0..15"""
        for (fy, doff, nb) in segs:
            d = y - fy
            if 0 <= d * (AW // 2) + x // 2 < nb:
                b = pakb[px_off + doff + d * (AW // 2) + x // 2]
                return (b >> 4) if (x & 1) else (b & 0x0F)
        return 0

    def window(x0, y0, w, h):
        return [[nib(x0 + x, y0 + y) for x in range(w)] for y in range(h)]

    items = []
    wide_rect = tuple(recs[0x7F - REC_BASE][2:])          # 「宽空格」矩形 (f364_patch 已记录)
    for code, (ch, slot) in sorted(BORROW.items()):
        ri = code - REC_BASE
        b0, b1, u0, v0, u1, v1 = recs[ri]
        rw, rh = u1 - u0, v1 - v0
        g = window(u0, v0, rw, rh)
        ink = sum(1 for row in g for v in row if v)
        x, y, row, col = cell_xy(slot, a.ncol, a.h)
        if (u0, v0, u1, v1) == wide_rect:
            note = ('★ 该记录矩形 == 「宽空格」矩形 %s ⇒ 图集里**没有**这个字的字形: '
                    '0x%02X 是**引擎图标码**, 图标由 DrawString 走独立绘制路径画出 (不吃字库) '
                    '⇒ 几何路必须从别处取 ✕ 字形 (UI 图标资源 / TTF), **不能** blit 本矩形。'
                    % (str(wide_rect), code))
            usable = False
        else:
            note = ('记录矩形就是该单字节码的字形采样窗 (墨 %d) ⇒ 可直接 blit 到 target_cell。'
                    % ink)
            usable = True
        items.append(dict(code='0x%02X' % code, char=ch, record_index=ri,
                          record=(b0, b1, u0, v0, u1, v1), rect_wh=[rw, rh], ink=ink,
                          usable_as_glyph=usable, source_note=note,
                          slot=slot, target_cell=[x, y], target_row_col=[row, col],
                          bitmap=g))
        print('  [gly] 0x%02X %-4s 记录 %3d rect=(%d,%d)-(%d,%d) %dx%d 墨 %3d ⇒ slot %d '
              '格 (%d,%d) = row %d col %d %s'
              % (code, ch, ri, u0, v0, u1, v1, rw, rh, ink, slot, x, y, row, col,
                 '' if usable else '  ← 图标码, 记录里不是字形'))

    # ── 写 PNG (放大 8×) + JSON + .txt ──
    try:
        from PIL import Image
        have_pil = True
    except Exception:                                                # noqa: BLE001
        have_pil = False
    for it in items:
        g = it['bitmap']
        if have_pil:
            im = Image.new('L', (len(g[0]), len(g)), 255)
            px = im.load()
            for yy, row in enumerate(g):
                for xx, v in enumerate(row):
                    px[xx, yy] = 255 - min(255, v * 17)
            im = im.resize((len(g[0]) * 8, len(g) * 8), Image.NEAREST)
            p = os.path.join(out, 'glyph_slot%04d_code%02X.png' % (it['slot'], int(it['code'], 16)))
            im.save(p)
            it['png'] = os.path.basename(p)
    # 对偶码回填
    for it in items:
        sl = it['slot']
        it['pair'] = [0xB9, 0xFA + (sl - 2345)]
        it['pair_hex'] = '0x%02X%02X' % tuple(it['pair'])
    with open(os.path.join(out, 'glyph_handoff.json'), 'w', encoding='utf-8',
              newline='\n') as f:
        json.dump(dict(src=os.path.abspath(a.iso), gate=gate,
                       target_geometry=dict(ncol=a.ncol, h=a.h, skip_rows=3, y0=2),
                       note='借槽字的原字形 (来自单字节码的 FONT.RES 记录矩形) + 目标图集格; '
                            '几何路把 bitmap blit 到 target_cell 即完成这 5 个槽的字形。'
                            'bitmap 值 = 4bit 调色索引 (0 = 透明/背景)。',
                       items=[{k: v for k, v in it.items()} for it in items]),
                  f, ensure_ascii=False, indent=1)
    print('[out] %s' % os.path.join(out, 'glyph_handoff.json'))
    print('[note] 记录矩形 → 图集窗: 采样原点 (u0,v0), 尺寸 %s ; 逐格已按 GIF 封包行映射取墨'
          % ([it['rect_wh'] for it in items][0]))
    iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
