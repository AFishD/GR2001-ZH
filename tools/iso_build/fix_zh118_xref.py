# -*- coding: utf-8 -*-
r"""fix_zh118_xref.py — find call sites / data pointers in an EE RAM image.

  --jal 0x3F5FD0     every `jal 0x3F5FD0` call site (and the whole function's)
  --word 0x00193E90  every 4-byte occurrence of a value (vtable slots, data ptrs)
  --ascii "TEXT"     every occurrence of an ASCII string

Usage:
  python tools/iso_build/fix_zh118_xref.py --ram <eeram.bin> --jal 0x3F5FD0 --jal 0x366A40
"""
import argparse
import struct
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--ram', required=True)
    ap.add_argument('--jal', action='append', default=[])
    ap.add_argument('--word', action='append', default=[])
    ap.add_argument('--ascii', action='append', default=[])
    ap.add_argument('--window', type=int, default=8, help='bytes of context')
    ap.add_argument('--limit', type=int, default=40)
    a = ap.parse_args()
    d = open(a.ram, 'rb').read()
    print('RAM = %s (%d B)' % (a.ram, len(d)))

    for spec in a.jal:
        tgt = int(spec, 0)
        enc = struct.pack('<I', 0x0C000000 | ((tgt >> 2) & 0x03FFFFFF))
        hits = []
        st = 0
        while True:
            k = d.find(enc, st)
            if k < 0:
                break
            hits.append(k)
            st = k + 1
        print('\n== jal %08X (encoded %s): %d call sites ==' % (tgt, enc.hex().upper(), len(hits)))
        for k in hits[:a.limit]:
            print('   call at %08X' % k)

    for spec in a.word:
        v = int(spec, 0)
        pat = struct.pack('<I', v)
        hits = []
        st = 0
        while True:
            k = d.find(pat, st)
            if k < 0:
                break
            hits.append(k)
            st = k + 1
        print('\n== word %08X: %d occurrences ==' % (v, len(hits)))
        for k in hits[:a.limit]:
            lo = max(0, k - a.window)
            ctx = d[lo:k + 4 + a.window]
            print('   at %08X   ctx[%08X]: %s' % (k, lo, ' '.join('%02X' % b for b in ctx)))

    for s in a.ascii:
        b = s.encode('latin-1')
        hits = []
        st = 0
        while True:
            k = d.find(b, st)
            if k < 0:
                break
            hits.append(k)
            st = k + 1
        print('\n== ascii %r: %d occurrences ==' % (s, len(hits)))
        for k in hits[:a.limit]:
            print('   at %08X' % k)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
