# -*- coding: utf-8 -*-
r"""m24_row20.py — 行20 的 lead-0xAE 空闲槽逐个查: 到底谁与引擎格相交?
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
NEW_GATE = 0xAE
PHI = {19: 2, 20: 2, 21: 2}


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
js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
used = {(b0 - 0xA1) * 94 + (b1 - 0xA1) for (b0, b1) in pair_of.values()}

WINS = []
for ch, (b0, b1) in pair_of.items():
    if b0 >= NEW_GATE:
        continue
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    r, c = s // 62, s % 62
    WINS.append((16 * ((c + PHI.get(r, 0)) % 64), yrow(r), 'pair %02X%02X %s' % (b0, b1, ch)))
for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(faces[FI[fname]][2]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        WINS.append(((u0 + 576) % 1024, v0 + 1, 'eng %s 0x%02X' % (fname, code + 0x20)))


def inter(a, b):
    return not (a[0] + 16 <= b[0] or b[0] + 16 <= a[0] or a[1] + 16 <= b[1] or b[1] + 16 <= a[1])


print('行20 空闲槽 (lead 0xAE) 引擎格相交明细:')
for s in sorted(x for x in range(1240, 1302) if x not in used):
    c = s - 1240
    x, y = 16 * ((c + 2) % 64), yrow(20)
    hits = [(wx, wy, tag) for (wx, wy, tag) in WINS if inter((x, y), (wx, wy))]
    print('  slot %4d 码 %02X%02X C=%2d 引擎格=(%4d,%3d) 相交 %2d  %s'
          % (s, 0xA1 + s // 94, 0xA1 + s % 94, c, x, y, len(hits),
             '; '.join('%s@(%d,%d)' % (t[2], t[0], t[1]) for t in hits[:4])))
