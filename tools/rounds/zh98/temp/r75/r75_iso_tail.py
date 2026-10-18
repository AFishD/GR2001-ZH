# -*- coding: utf-8 -*-
"""r75_iso_tail.py -- ISO9660: MENU.IMG 的声明大小 / 所在 LBA / 后面还剩多少扇区。"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..'))
SEC = 2048


def pvd(f):
    f.seek(16 * SEC)
    d = f.read(SEC)
    root = d[156:156 + 34]
    return struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]


def walk(f, lba, size, depth=0, out=None):
    if out is None:
        out = []
    f.seek(lba * SEC)
    d = f.read(size)
    p = 0
    while p < len(d):
        ln = d[p]
        if ln == 0:
            p = (p // SEC + 1) * SEC
            if p >= len(d):
                break
            continue
        rec = d[p:p + ln]
        elba = struct.unpack_from('<I', rec, 2)[0]
        esz = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33 + nlen].decode('latin-1')
        if name not in ('\x00', '\x01'):
            out.append((name, elba, esz, flags, depth))
        if flags & 2 and name not in ('\x00', '\x01') and depth < 3:
            walk(f, elba, esz, depth + 1, out)
        p += ln
    return out


for iso in (r'work\builds\GR_EN_ORIG\GR_EN_ORIG.iso', r'work\builds\GR_ZH113b\GR_ZH113b.iso'):
    p = os.path.join(REPO, iso)
    sz = os.path.getsize(p)
    print('==', iso, 'size=%d sectors=%d' % (sz, sz // SEC))
    with open(p, 'rb') as f:
        out = walk(f, *pvd(f))
    out.sort(key=lambda x: x[1])
    for nm, lba, esz, fl, dep in out:
        if lba > 700000:
            print('   %-16s LBA=%-8d size=%-11d end=%-8d' % (nm, lba, esz, lba + (esz + SEC - 1) // SEC))
    m = [x for x in out if x[0].startswith('MENU.IMG')]
    if m:
        nm, lba, esz, fl, dep = m[0]
        print('   MENU.IMG LBA=%d size=%d end_sector=%d  ISO_end=%d  tail_slack=%d sectors'
              % (lba, esz, lba + (esz + SEC - 1) // SEC, sz // SEC,
                 sz // SEC - (lba + (esz + SEC - 1) // SEC)))
