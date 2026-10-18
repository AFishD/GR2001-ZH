# -*- coding: utf-8 -*-
r"""m22_row21.py — 行21 的 14 个空闲槽 (1302..1315) 逐格归因: 谁与我的写入框相交?
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
PHI = {19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


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
used_slots = {(b0 - 0xA1) * 94 + (b1 - 0xA1) for (b0, b1) in pair_of.values()}

WINS = []
for ch, (b0, b1) in pair_of.items():
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    if R in PHI:
        WINS.append((16 * ((C + PHI[R]) % 64), yrow(R), 'pair %02X%02X %s' % (b0, b1, ch)))
    else:
        WINS.append((16 * C, yrow(R), 'pair(16C) %s' % ch))
for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(faces[FI[fname]][2]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        WINS.append((u0, v0, 'FTrec %s 0x%02X' % (fname, code + 0x20)))
        WINS.append(((u0 + 576) % W, v0 + 1, 'FTeng576 %s 0x%02X' % (fname, code + 0x20)))
        for rr, ph in PHI.items():
            if yrow(rr) == v0:
                WINS.append(((u0 + 16 * ph) % W, v0 + 1, 'FTengPHI %s 0x%02X' % (fname, code + 0x20)))


def inter(a, b):
    return not (a[0] + 16 <= b[0] or b[0] + 16 <= a[0] or a[1] + 16 <= b[1] or b[1] + 16 <= a[1])


print('行21 空闲槽逐格归因 (只列相交窗口数 + 前 3 条):')
for s in list(range(1302, 1316)) + [1246, 1245, 1273, 1274]:
    if s in used_slots:
        print('  slot %d 已被占用' % s)
        continue
    R, C = s // 62, s % 62
    ph = PHI.get(R)
    x = 16 * ((C + ph) % 64) if ph is not None else 16 * C
    y = yrow(R)
    hits = [(wx, wy, tag) for (wx, wy, tag) in WINS if inter((x, y), (wx, wy))]
    hit_t = [(wx, wy, tag) for (wx, wy, tag) in WINS if inter((4 + 16 * C, y), (wx, wy))]
    print('  slot %4d (%02X%02X) R=%d C=%2d  引擎格=(%4d,%3d) 相交 %d  %s'
          % (s, 0xA1 + s // 94, 0xA1 + s % 94, R, C, x, y, len(hits),
             '; '.join('%s@(%d,%d)' % (t[2], t[0], t[1]) for t in hits[:3])))
    print('        tcs格=(%4d,%3d) 相交 %d  %s'
          % (4 + 16 * C, y, len(hit_t),
             '; '.join('%s@(%d,%d)' % (t[2], t[0], t[1]) for t in hit_t[:3])))
