# -*- coding: utf-8 -*-
r"""p06_icon_strip.py — round42: 原版 512x512/8bpp 字体图集上的「按键图标条」 vs 中文化的 1024x512/4bpp

动机 (p05): EN_ORIG 的 new_font_revised 是 **512x512 PSM8**; ZH93 的是 **1024x512 PSM4**。
            ⇒ 同一像素坐标 (1,198)-(21,218) / (25,198)-(45,218) 在两盘上完全不是一回事。
本脚本:
  ① EN_ORIG: 用**正确 stride (w)** 抠出 y=170..230, x=0..200, 放大 8 倍 → PNG + ASCII 图;
  ② ZH93  : 用 4bpp stride 抠同一块 → PNG;
  ③ 现役盘 GR_ZH93 的 ELF (LBA 295) 里 DrawString v1 的图标 UV 常量还在不在 (逐字比对原版)。
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

ELF_LBA = 295
SEC = 2048
X0, Y0, X1, Y1 = 0, 170, 200, 232


def load_atlas(iso_path):
    iso = tcslib.Iso(iso_path)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    iso.close()
    for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
        if nm == 'new_font_revised':
            return dict(psm=psm, w=w, h=h, off=off, pak=pak)
    return None


def texel(a, x, y):
    if a['psm'] == 0x14:                       # PSMT4: 偶 x 低 nibble
        b = a['pak'][a['off'] + y * (a['w'] // 2) + (x >> 1)]
        return (b & 0xF) if (x & 1) == 0 else (b >> 4)
    b = a['pak'][a['off'] + y * a['w'] + x]    # PSMT8
    return b


for tag, iso_p in (('EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG',
                                            'GR_EN_ORIG.iso')),
                   ('ZH93', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))):
    a = load_atlas(iso_p)
    print('=' * 78)
    print('%s: new_font_revised %dx%d psm=0x%02X  (PSMT%d)'
          % (tag, a['w'], a['h'], a['psm'], 4 if a['psm'] == 0x14 else 8))
    print('=' * 78)
    buf = bytearray((X1 - X0) * (Y1 - Y0))
    for y in range(Y0, Y1):
        for x in range(X0, X1):
            buf[(y - Y0) * (X1 - X0) + (x - X0)] = 0 if texel(a, x, y) == 0 else 255
    im = Image.frombytes('L', (X1 - X0, Y1 - Y0), bytes(buf))
    im = im.convert('1', dither=Image.Dither.NONE).convert('L')
    p = os.path.join(HERE, 'strip_%s.png' % tag)
    im.resize(((X1 - X0) * 8, (Y1 - Y0) * 8), Image.NEAREST).save(p)
    print('  → %s (x=%d..%d, y=%d..%d, 放大 8 倍)' % (os.path.basename(p), X0, X1, Y0, Y1))
    print('  ASCII 图 (每行 = 图集一行; 只画 x=0..99, 每 10 列一个标尺):')
    print('        ' + ''.join(str((x // 10) % 10) for x in range(0, 100)))
    for y in range(Y0, Y1):
        row = ''.join('#' if texel(a, x, y) == 0 else '.' for x in range(0, 100))
        print('   %3d  %s' % (y, row))
    print()

# ── ③ 现役盘 ELF 的图标 UV 常量 ──
print('=' * 78)
print('现役盘 GR_ZH93 的 ELF (LBA %d) — DrawString v1 图标特判逐字比对' % ELF_LBA)
print('=' * 78)
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))
cur = iso.read(ELF_LBA * SEC, 0x4DED80)
iso.close()
orig = open(os.path.join(REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13'),
            'rb').read()
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
CHECKS = [(0x219C08, '0xB5 比较 #1'), (0x219C10, '0xB5 比较 #1 延迟槽'), (0x219C14, '0xB1 比较 #1'),
          (0x219C4C, 'UV 1.0'), (0x219C54, 'UV 198.0'), (0x219C5C, 'UV 21.0'), (0x219C64, 'UV 218.0'),
          (0x219C70, 'UV 25.0'), (0x219C80, 'UV 45.0'),
          (0x219C94, '0xB5 比较 #2'), (0x219CAC, '0xB1 比较 #2'),
          (0x219D24, '0xB5 比较 #3'), (0x219D38, '0xB1 比较 #3')]
for va, label in CHECKS:
    o = struct.unpack_from('<I', orig, SEC_OFF + va - SEC_ADDR)[0]
    c = struct.unpack_from('<I', cur, SEC_OFF + va - SEC_ADDR)[0]
    print('  %08X  %-18s 原版 %08X   现役 %08X   %s'
          % (va, label, o, c, '一致 ✓' if o == c else '**不同**'))
# 整段一致性
for lo, hi, name in ((0x219C40, 0x219C94, '0xB5/0xB1 的 UV 硬编码块'),
                     (0x219D1C, 0x219D80, '图标码第二次比较 + AddOneWord 块')):
    same = all(struct.unpack_from('<I', orig, SEC_OFF + i - SEC_ADDR)[0]
               == struct.unpack_from('<I', cur, SEC_OFF + i - SEC_ADDR)[0]
               for i in range(lo, hi, 4))
    print('  段 %-40s 0x%08X..0x%08X  %s' % (name, lo, hi, '逐字节一致 ✓' if same else '**有差异**'))
