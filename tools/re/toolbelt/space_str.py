# -*- coding: utf-8 -*-
r"""space_str.py -- 在 ELF / IMG 里搜 ASCII 字面量 + 8bpp 调色板占用统计（只读）。"""
import argparse
import os
import re
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
ELF_LBA = 295


def strings_search(data, pats, limit=8):
    out = {}
    for p in pats:
        b = p.encode('ascii')
        hits = []
        st = 0
        while True:
            i = data.find(b, st)
            if i < 0:
                break
            hits.append(i)
            st = i + 1
            if len(hits) > 200:
                break
        out[p] = hits[:limit]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'GR_ZH98_x.json'))
    a = ap.parse_args()
    iso = tcslib.Iso(a.iso)

    pats = ['COMMON.PAK', 'common.pak', 'new_font_revised', 'new_font', 'FONT.RES', 'font.res',
            'MENU.IMG', 'menu.img', 'GR.IMG', 'grame', 'MODULES', 'cdrom0:', 'pda-lcd-02',
            'pda_counterparts', 'arrow', 'texture', 'RSB', '.rsb', 'LOAD_NEW_1']
    # 1) ELF
    elf = iso.read(ELF_LBA * SEC, 37453732)
    print('== ELF (%d B) 字面量 ==' % len(elf))
    for k, v in strings_search(elf, pats).items():
        if v:
            print('  %-20s n=%d first=0x%X  %s' % (k, len(v), v[0],
                  elf[max(0, v[0] - 24):v[0] + len(k) + 24]))
    # 2) MENU.IMG 头部 64KB
    menu = iso.read(776286 * SEC, 0x10000)
    print('\n== MENU.IMG 头 64KB ==')
    for k, v in strings_search(menu, pats).items():
        if v:
            print('  %-20s n=%d first=0x%X' % (k, len(v), v[0]))
    # 3) GR.IMG 头 256KB
    gr = iso.read(19175 * SEC, 0x40000)
    print('\n== GR.IMG 头 256KB ==')
    for k, v in strings_search(gr, pats).items():
        if v:
            print('  %-20s n=%d first=0x%X' % (k, len(v), v[0]))
    iso.close()


main()
