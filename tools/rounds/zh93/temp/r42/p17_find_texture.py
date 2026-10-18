# -*- coding: utf-8 -*-
r"""p17_find_texture.py — round42: 找 `pda_counterparts.rsb` 到底是哪个文件 (COMMON.PAK 记录? 还是独立 RSB?)

ELF 里图标 model 的纹理名是 C 字符串 "pda_counterparts.rsb" (VA 0x578650),
经 UITextureMgr::GetTexture(RSFilename&) 装载 —— 那是**按文件名**找资源, 不一定是
COMMON.PAK 里那条同名记录。本脚本在 MENU.IMG / GR.IMG 的条目名表 + ISO 目录里找它。
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402

for tag, iso_p in (('EN_ORIG', os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG',
                                            'GR_EN_ORIG.iso')),
                   ('ZH93', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))):
    iso = tcslib.Iso(iso_p)
    print('=' * 78)
    print('%s' % tag)
    print('=' * 78)
    for img, lba in (('MENU.IMG', tcslib.MENU_LBA), ('GR.IMG', tcslib.GR_LBA)):
        base = lba * 2048
        noff = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
        nend = struct.unpack_from('<I', iso.mm, base + 4)[0]
        names = [x.decode('latin-1') for x in
                 bytes(iso.mm[base + noff:base + nend]).split(b'\x00') if x]
        hit = [(i, n) for i, n in enumerate(names)
               if 'counterpart' in n.lower() or 'pda' in n.lower()
               or 'font' in n.lower() or 'icon' in n.lower()]
        print('  %-9s 条目名 %d 个; 命中 pda/font/icon/counterpart: %d'
              % (img, len(names), len(hit)))
        for i, n in hit[:40]:
            e = iso.img_entry(lba, i)
            print('     #%-5d %-28s stored=%-9d real=%-9d off=0x%X'
                  % (i, n, e['stored'], e['real'], e['off']))
    # ISO9660 目录里的文件名
    try:
        import pycdlib                                          # noqa: F401
        have = True
    except Exception:                                           # noqa: BLE001
        have = False
    print('  (ISO9660 目录扫描: %s)' % ('用 pycdlib' if have else '无 pycdlib, 跳过'))
    if have:
        import pycdlib
        cd = pycdlib.PyCdlib()
        cd.open(iso_p)
        found = []
        for root, dirs, files in cd.walk():
            for f in files:
                if re.search(r'counterpart|pda', f, re.I):
                    found.append((root, f))
        print('    命中: %s' % (found[:20] or '无'))
        cd.close()
    iso.close()
    print()
