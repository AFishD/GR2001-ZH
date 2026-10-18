# -*- coding: utf-8 -*-
r"""m15_why.py — 为什么 lead 0xAE 的空闲槽格子会与"活窗"相交? 逐窗归因。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
CS = tcslib.CHARSET
W, H, CW, CH = 1024, 512, 16, 16
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


iso = tcslib.Iso(BASE)
ft_e = pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
    elif e['name'] == 'FONT.RES':
        ft_e = e
ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
iso.close()
_he, faces = tcslib.parse_ft_faces(ft_blob)
FI = {f[0]: i for i, f in enumerate(faces)}
js = json.load(open(CS, encoding='utf-8'))
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}

WINS = []       # (x, y, tag)


def addbox(x, y, tag):
    WINS.append((x, y, tag))


for ch, (b0, b1) in pair_of.items():
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    addbox(16 * ((C + PHI[R]) % 64), yrow(R) + (1 if C + PHI[R] >= 64 else 0),
           'pair %02X%02X %s' % (b0, b1, ch))
for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(faces[FI[fname]][2]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        addbox(u0, v0, 'FTrec %s 0x%02X' % (fname, code + 0x20))
        addbox((u0 + 576) % W, v0 + 1, 'FTeng %s 0x%02X' % (fname, code + 0x20))


def inter(a, b):
    return not (a[0] + CW <= b[0] or b[0] + CW <= a[0]
                or a[1] + CH <= b[1] or b[1] + CH <= a[1])


for (s, note) in ((1245, 'AEB8'), (1244, 'AEB7'), (1246, 'AEB9'), (1284, 'AEDF'),
                  (1278, 'AED9'), (1300, 'AEEF'), (1315, 'AEFE'), (1302, 'AEF1')):
    R, C = s // 62, s % 62
    x, y = 16 * ((C + PHI[R]) % 64), yrow(R)
    xt = 4 + 16 * C
    print('== slot %d %s: 引擎格 (%d,%d), tcs 格 (%d,%d)' % (s, note, x, y, xt, y))
    for label, bx in (('引擎格', (x, y)), ('tcs格', (xt, y))):
        hits = [(wx, wy, tag) for (wx, wy, tag) in WINS if inter(bx, (wx, wy))]
        print('   %s 相交窗口 %d 个:' % (label, len(hits)))
        for (wx, wy, tag) in hits[:8]:
            ox = max(0, min(bx[0] + CW, wx + CW) - max(bx[0], wx))
            oy = max(0, min(bx[1] + CH, wy + CH) - max(bx[1], wy))
            print('      (%4d,%3d) %-24s 交叠 %dx%d px' % (wx, wy, tag, ox, oy))
    print()
