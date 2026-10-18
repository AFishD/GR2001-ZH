# -*- coding: utf-8 -*-
r"""p05_texture_probe.py — round42: 到底哪张纹理上有「按键图标」? (只读)

动机: DrawString v1 给文本图标码 0xB1/0xB5 硬编码了 UV
        0xB5 → (1,198)-(21,218)      0xB1 → (25,198)-(45,218)
      但字体图集 new_font_revised 里这两块几乎没墨 (EN_ORIG 墨 1/0)。
      ⇒ 要么图标在**另一张纹理**上, 要么这两块在图集里另有位置。
      本脚本: ① 列出 COMMON.PAK 的全部记录 (名字/尺寸/psm);
              ② 在所有**看起来像图集**的记录上, 量那两块 UV 的墨量;
              ③ 把字体图集 y=180..230 的 ASCII 图打出来看。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402

BOXES = [('0xB5 text icon', (1, 198, 21, 218)), ('0xB1 text icon', (25, 198, 45, 218)),
         ('shortcut 26/28', (0, 178, 20, 198)), ('shortcut 29', (21, 178, 41, 198)),
         ('shortcut 30', (42, 178, 62, 198)), ('shortcut 31', (63, 178, 83, 198)),
         ('shortcut 27', (85, 178, 120, 198))]

for tag, iso_p in (('EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG',
                                            'GR_EN_ORIG.iso')),
                   ('ZH93', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))):
    if not os.path.isfile(iso_p):
        continue
    iso = tcslib.Iso(iso_p)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    iso.close()
    recs = tcslib.parse_pak_records(pak)
    print('=' * 78)
    print('%s: COMMON.PAK 共 %d 条记录' % (tag, len(recs)))
    print('=' * 78)
    print('  %-28s %-6s %5s %5s %8s %9s' % ('name', 'psm', 'w', 'h', 'clut', 'px_size'))
    for (nm, psm, w, h, clut, px, off) in recs:
        mark = ' ★字体图集候选' if (w * h >= 65536 and psm in (0x14, 0x13, 0x00)) else ''
        print('  %-28s 0x%02X  %5d %5d %8d %9d%s' % (nm, psm, w, h, clut, px, mark))

    # 在每条 4bpp (psm=0x14) 或 8bpp (0x13) 记录上量那两个 UV 框
    for (nm, psm, w, h, clut, px, off) in recs:
        if psm not in (0x14, 0x13, 0x00) or w * h < 4096:
            continue
        print()
        print('  ── 在 %s (%dx%d psm=0x%02X) 上量关键 UV 框的墨量:' % (nm, w, h, psm))
        for label, (u0, v0, u1, v1) in BOXES:
            if u1 > w or v1 > h:
                print('     %-16s (%3d,%3d)-(%3d,%3d): **超出纹理**' % (label, u0, v0, u1, v1))
                continue
            n = 0
            if psm == 0x14:
                stride = w // 2
                for y in range(v0, v1):
                    base = off + y * stride
                    for x in range(u0, u1):
                        b = pak[base + (x >> 1)]
                        t = (b & 0xF) if (x & 1) == 0 else (b >> 4)
                        if t == 0:
                            n += 1
            else:
                for y in range(v0, v1):
                    for x in range(u0, u1):
                        if pak[off + y * w + x] != 0:
                            n += 1
            print('     %-16s (%3d,%3d)-(%3d,%3d): 墨 %d' % (label, u0, v0, u1, v1, n))

    # ASCII 图: 字体图集 y=180..230, x=0..120
    fa = [r for r in recs if r[0] == 'new_font_revised']
    if fa and fa[0][1] == 0x14:
        nm, psm, w, h, clut, px, off = fa[0]
        print()
        print('  ── %s ASCII 图 (x=0..119, y=180..229; #=墨 .=空; 每 10 行画一条标尺)' % nm)
        stride = w // 2
        print('      ' + ''.join(str((x // 10) % 10) for x in range(0, 120)))
        for y in range(180, min(h, 230)):
            row = []
            base = off + y * stride
            for x in range(0, 120):
                b = pak[base + (x >> 1)]
                t = (b & 0xF) if (x & 1) == 0 else (b >> 4)
                row.append('#' if t == 0 else '.')
            print('  %3d %s' % (y, ''.join(row)))
    print()
