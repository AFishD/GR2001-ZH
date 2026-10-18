# -*- coding: utf-8 -*-
r"""ramdiff.py -- byte-level differential between two EE RAM images, summarised
by 64 KiB block, plus a focused diff of the allocator mstate region and the low
(exception-vector) region.

usage: python ramdiff.py <a.bin|a.p2s> <b.bin|b.p2s> [label]
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p2s

RAM = 32 * 1024 * 1024
BLK = 0x10000
REGIONS = [
    ('exception vectors / low RAM', 0x00000000, 0x00000400),
    ('low RAM 0x400..0x10000', 0x00000400, 0x00010000),
    ('allocator mstate + bins', 0x0055B7A0, 0x0055C200),
    ('heap (whole arena)', 0x0065AEA0, 0x01F98020),
]


def load(p):
    if p.lower().endswith(('.p2s', '.backup')):
        return p2s.ee_ram(p)
    return open(p, 'rb').read()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    a = load(sys.argv[1])
    b = load(sys.argv[2])
    label = sys.argv[3] if len(sys.argv) > 3 else 'diff'
    print('== %s' % label)
    print('   A=%s' % sys.argv[1])
    print('   B=%s' % sys.argv[2])
    total = 0
    blocks = []
    for off in range(0, RAM, BLK):
        d = sum(1 for i in range(off, min(off + BLK, RAM), 1024)
                if a[i:i + 1024] != b[i:i + 1024])
        if d:
            # exact count for changed blocks only
            n = sum(1 for i in range(off, min(off + BLK, RAM)) if a[i] != b[i])
            total += n
            blocks.append((n, off))
    print('   differing bytes (whole 32 MiB): %d' % total)
    blocks.sort(reverse=True)
    print('   top 12 differing 64 KiB blocks:')
    for n, off in blocks[:12]:
        print('      0x%08X..0x%08X  %7d bytes' % (off, off + BLK - 1, n))
    for name, lo, hi in REGIONS:
        n = sum(1 for i in range(lo, hi) if a[i] != b[i])
        addrs = [i for i in range(lo, hi) if a[i] != b[i]]
        print('   region %-28s 0x%08X..0x%08X : %6d differing bytes' % (name, lo, hi - 1, n))
        if addrs and n <= 64:
            segs = []
            s = addrs[0]
            p = addrs[0]
            for x in addrs[1:]:
                if x == p + 1:
                    p = x
                    continue
                segs.append((s, p))
                s = p = x
            segs.append((s, p))
            for s, e in segs[:20]:
                print('       0x%08X..0x%08X  A=%s  B=%s'
                      % (s, e, ' '.join('%02X' % x for x in a[s:e + 1]),
                         ' '.join('%02X' % x for x in b[s:e + 1])))


if __name__ == '__main__':
    main()
