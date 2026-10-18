# -*- coding: utf-8 -*-
"""r75_holes.py -- are the MENU.IMG gaps really zero-filled (usable as relocation targets)?"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..'))
MENU_LBA, SEC = 776286, 2048
HOLES = [
    ('IT_MESSAGE_MC_3 -> DE_STRINGS.RES', 0x20D0EC, 0x218B00),
    ('MISSILE.PRJ -> EN_STRINGS.RES', 0x2CC1068, 0x377E000),
    ('MENU.IMG tail slack (after EN_STRINGS.TXT)', 0x378AA9E, 58300882),
]
for iso in (r'work\builds\GR_EN_ORIG\GR_EN_ORIG.iso', r'work\builds\GR_ZH113b\GR_ZH113b.iso'):
    p = os.path.join(REPO, iso)
    print('==', iso)
    with open(p, 'rb') as f:
        for nm, a, b in HOLES:
            f.seek(MENU_LBA * SEC + a)
            d = f.read(b - a)
            nz = sum(1 for x in d if x)
            print('   %-34s len=%-10d nonzero=%-9d (%.4f%%)' % (nm, len(d), nz, 100.0 * nz / len(d)))
