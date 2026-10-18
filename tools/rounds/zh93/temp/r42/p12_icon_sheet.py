# -*- coding: utf-8 -*-
r"""p12_icon_sheet.py — round42: 把「手柄按键图标图集」pda_counterparts (256x256 PSMT8) 抠成 PNG

ELF 证据:
  RSFontMgr::ReadResourceFile @0x219380 尾部把**第二个** UISpriteModel (this+76, 容量 2 quad)
  的纹理设成 C 字符串 "pda_counterparts.rsb" (VA 0x578650)。
  DrawString v1 @0x219C40.. 对**文本图标码** 0xB5/0xB1 直接硬编码 UV:
      0xB5 → (u 1..21, v 198..218)
      0xB1 → (u 25..45, v 198..218)
  kShortcutDefaultTC @0x2BEFE0 给「快捷键图标索引」的 UV:
      26/28 → (0,178)-(20,198)   29 → (21,178)-(41,198)   30 → (42,178)-(62,198)
      31    → (63,178)-(83,198)  27 → (85,178)-(120,198)
  ⇒ 全部落在 256x256 之内 ⇒ 这些 UV 说的就是 pda_counterparts 这张图。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402
from PIL import Image                                            # noqa: E402

ISO_ORIG = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
ISO_ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
NAME = 'pda_counterparts'


def grab(iso_path, name):
    iso = tcslib.Iso(iso_path)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    iso.close()
    base = 0
    while base + 8 <= len(pak):
        ty, nl = struct.unpack_from('<II', pak, base)
        if ty == 0x63 or nl > 64:
            break
        nm = pak[base + 8:base + 8 + nl].decode('latin-1')
        q = base + 8 + nl
        psm, w, h, clut = struct.unpack_from('<4I', pak, q)
        pxoff = q + 16 + clut
        pxsz = struct.unpack_from('<I', pak, q + 16 + clut)[0]
        if nm == name:
            cl = pak[q + 16:q + 16 + clut]
            px = pak[pxoff + 4: pxoff + 4 + pxsz]
            return dict(psm=psm, w=w, h=h, cl=cl, px=px, name=nm)
        base = pxoff + 4 + pxsz
    return None


for tag, iso in (('EN_ORIG', ISO_ORIG), ('ZH93', ISO_ZH)):
    r = grab(iso, NAME)
    if not r:
        print('[skip] %s 里找不到 %s' % (tag, NAME))
        continue
    w, h, psm, cl, px = r['w'], r['h'], r['psm'], r['cl'], r['px']
    # CLUT: 实测 clut 段 = 16B 头 + 256*4B (R,G,B,A)
    clut = cl[16:16 + 1024] if len(cl) >= 1040 else cl
    print('=' * 78)
    print('%s: %s %dx%d psm=0x%02X, 像素 %d B, CLUT %d B'
          % (tag, r['name'], w, h, psm, len(px), len(cl)))
    print('=' * 78)

    def rgba(i):
        o = i * 4
        if o + 3 >= len(clut):
            return (255, 0, 255, 255)
        R, G, B, A = clut[o], clut[o + 1], clut[o + 2], clut[o + 3]
        if i == 0:
            return (0, 0, 0, 0)
        return (R, G, B, 255 if A == 0 else A)

    im = Image.new('RGBA', (w, h))
    pix = im.load()
    for y in range(h):
        for x in range(w):
            pix[x, y] = rgba(px[y * w + x])
    # 白底合成, 便于肉眼看
    bg = Image.new('RGBA', (w, h), (255, 255, 255, 255))
    comp = Image.alpha_composite(bg, im).convert('RGB')
    p1 = os.path.join(HERE, 'iconsheet_%s.png' % tag)
    comp.resize((w * 3, h * 3), Image.NEAREST).save(p1)
    print('  → %s (%dx%d, 放大 3 倍)' % (os.path.basename(p1), w * 3, h * 3))
    # 图标带 (v=170..225) 放大 8 倍
    crop = comp.crop((0, 168, 130, 226))
    p2 = os.path.join(HERE, 'iconband_%s.png' % tag)
    crop.resize((130 * 8, 58 * 8), Image.NEAREST).save(p2)
    print('  → %s (x=0..130, y=168..226, 放大 8 倍)' % os.path.basename(p2))
    # 逐行墨 (非透明) 统计, 找图标行
    print('  有内容的行区间 (索引 0 视为空):')
    rows = []
    for y in range(h):
        n = sum(1 for x in range(w) if px[y * w + x] != 0)
        rows.append(n)
    runs, cur = [], None
    for y in range(h):
        if rows[y] > 3 and cur is None:
            cur = y
        elif rows[y] <= 3 and cur is not None:
            runs.append((cur, y)); cur = None
    if cur is not None:
        runs.append((cur, h))
    print('    %s' % ' '.join('%d..%d(%d)' % (a, b, max(rows[a:b])) for a, b in runs))
    print('  关键 UV 框里的非透明像素数:')
    for label, (u0, v0, u1, v1) in (('文本码 0xB5 (1,198)-(21,218)', (1, 198, 21, 218)),
                                    ('文本码 0xB1 (25,198)-(45,218)', (25, 198, 45, 218)),
                                    ('shortcut 26/28 (0,178)-(20,198)', (0, 178, 20, 198)),
                                    ('shortcut 29 (21,178)-(41,198)', (21, 178, 41, 198)),
                                    ('shortcut 30 (42,178)-(62,198)', (42, 178, 62, 198)),
                                    ('shortcut 31 (63,178)-(83,198)', (63, 178, 83, 198)),
                                    ('shortcut 27 (85,178)-(120,198)', (85, 178, 120, 198))):
        n = sum(1 for y in range(v0, v1) for x in range(u0, u1) if px[y * w + x] != 0)
        print('    %-32s 非空 %d' % (label, n))
    print()
