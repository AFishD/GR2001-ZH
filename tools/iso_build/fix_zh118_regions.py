# -*- coding: utf-8 -*-
r"""fix_zh118_regions.py — compare byte regions between two EE RAM images and
against the pristine ELF segment, and dump the low-RAM header.

Usage:
  python tools/iso_build/fix_zh118_regions.py --a <eeram.bin> [--b <eeram2.bin>]
      [--ranges 0x0:0x200,0x3F5F00:0x3F6100]
"""
import argparse
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', default=None)
    ap.add_argument('--ranges', default='0x0:0x200,0x3F5F00:0x3F6100')
    ap.add_argument('--ascii', action='store_true')
    a = ap.parse_args()
    A = open(a.a, 'rb').read()
    B = open(a.b, 'rb').read() if a.b else None

    for spec in a.ranges.split(','):
        lo, hi = spec.split(':')
        lo = int(lo, 0)
        hi = int(hi, 0)
        print('===== RAM[%08X:%08X] =====' % (lo, hi))
        for off in range(lo, hi, 16):
            row = A[off:off + 16]
            s = '%08X  %s' % (off, ' '.join('%02X' % x for x in row))
            if a.ascii:
                s += '  |' + ''.join(chr(x) if 32 <= x < 127 else '.' for x in row) + '|'
            if B is not None:
                diff = sum(1 for i in range(len(row)) if A[off + i] != B[off + i])
                if diff:
                    s += '   DIFF(%d) B=%s' % (diff, ' '.join('%02X' % x for x in B[off:off + 16]))
            print(s)
        if B is not None:
            n = sum(1 for i in range(lo, hi) if A[i] != B[i])
            print('   -> differing bytes in range: %d / %d' % (n, hi - lo))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    raise SystemExit(main())
