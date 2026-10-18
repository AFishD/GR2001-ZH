# -*- coding: utf-8 -*-
r"""zero_hash5.py — 查特定条目是否在那张 4096 表里（决定"新条目名能否被 diSearchFile 找到"）
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)


def load(lba):
    base = lba * 2048
    hdr = struct.unpack_from('<12I', iso.mm, base)
    cnt = (hdr[3] - 0x830) // 48
    names = [x.decode('latin-1') for x in
             bytes(iso.mm[base + hdr[4]:base + hdr[1]]).split(b'\x00') if x]
    tab = struct.unpack_from('<4096I', iso.mm, base + hdr[8])
    idx2slot = {}
    for i in range(4096):
        v = tab[i]
        if v != 0xFFFFFFFF:
            idx2slot.setdefault(v, []).append(i)
    return hdr, cnt, names, idx2slot


for nm, lba in (('MENU.IMG', 776286), ('GR.IMG', 19175)):
    hdr, cnt, names, i2s = load(lba)
    print('=' * 78)
    print('%s: 头 %s' % (nm, ['0x%X' % v for v in hdr[:12]]))
    print('  表内不同条目下标 %d' % len(i2s))
    print('  条目 0..45 是否在表内:')
    for i in range(0, min(46, cnt)):
        print('    #%-4d %-28r %s' % (i, names[i], ('slot %s' % i2s[i]) if i in i2s else '— 不在'))
    # 关注的名字
    for want in ('LOAD_NEW_1.RSB', 'LOAD_NEW_2.RSB', 'VIDEO.RSB', 'SHORTCUT.RSB',
                 'COMMON.PAK', 'FONT.RES', 'ACTION.PAK', 'MENU.PAK', 'LOADING.PAK'):
        hits = [i for i, n in enumerate(names) if n.upper() == want]
        if hits:
            for i in hits:
                print('  ★ %-18s #%-5d %s' % (want, i, ('slot %s' % i2s[i]) if i in i2s else '— 不在表内'))

iso.close()
