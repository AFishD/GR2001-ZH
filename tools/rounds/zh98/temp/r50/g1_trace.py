# -*- coding: utf-8 -*-
"""r50 临时: 追踪 7 个字形的底行是在哪一步丢的。

对 GR_ZH94 (重排前) / GR_ZH95 (重排后) / GR_ZH97 / GR_ZH98 四张盘:
  用**该盘当时**的 charset 找到这 7 个字的槽位, 打印 (16,16) 位图与底行墨量。
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402

TARGETS = '叶奋姚娜孙宁宇'
DISKS = [
    ('GR_ZH94', 'work/builds/GR_ZH94/GR_ZH94.iso',
     'work/builds/GR_ZH94/font/charset_matching_this_disk.json'),
    ('GR_ZH95', 'work/builds/GR_ZH95/GR_ZH95.iso',
     'work/builds/GR_ZH95/temp/r46/charset_after_repack.json'),
    ('GR_ZH96_fix', 'work/builds/GR_ZH96_fix/GR_ZH96_fix.iso',
     'work/builds/GR_ZH98/temp/charset_before_font_cleanup.json'),
    ('GR_ZH97', 'work/builds/GR_ZH97/GR_ZH97.iso',
     'work/builds/GR_ZH98/temp/charset_before_font_cleanup.json'),
]


def cells_of(iso, charset):
    font = dump_font.load_font(iso)
    gray = dump_font.atlas_gray(font['atlas'], view='engine')
    W, H = font['atlas']['w'], font['atlas']['h']
    ink = (np.frombuffer(gray, np.uint8).reshape(H, W) == 0)
    return tcslib.Charset(charset), ink, H


def show(arr):
    return ['%2d %s' % (r, ''.join('#' if arr[r, c] else '.' for c in range(arr.shape[1])))
            for r in range(arr.shape[0])]


for tag, rel, csrel in DISKS:
    iso = os.path.join(REPO, rel)
    csp = os.path.join(REPO, csrel) if csrel else None
    cs, ink, H = cells_of(iso, csp)
    print('=' * 78)
    print('=== %s' % tag)
    for ch in TARGETS:
        p = cs.enc_pair.get(ch)
        if not p:
            print('  %s: 不在该盘 charset' % ch)
            continue
        slot = tcslib.pair_slot(*p)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        w = ink[y:y + 16, x:x + 16]
        below = int(ink[y + 16, x:x + 16].sum()) if y + 16 < H else -1
        print('  %s 码=%02X%02X slot=%4d row%2d col%2d 格=(%4d,%3d) 墨=%3d 底行墨=%2d 窗下1行墨=%d'
              % (ch, p[0], p[1], slot, slot // 62, slot % 62, x, y, int(w.sum()),
                 int(w[15].sum()), below))
        for line in show(w):
            print('       ' + line)
