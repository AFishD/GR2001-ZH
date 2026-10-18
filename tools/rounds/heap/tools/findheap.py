# -*- coding: utf-8 -*-
r"""findheap.py -- locate the dlmalloc heap extent inside an EE RAM image.

Verified chunk layout (from dis_00102050_001026B0.txt):
  chunk+0x00 prev_foot (8B) ; chunk+0x08 head (8B, size = head & 0x1FFFFFFE)
  chunk+0x10 fd (4B)        ; chunk+0x14 bk (4B)      ; mem = chunk+0x10
  next chunk = chunk + size ; sizes are multiples of 16, min 32

usage: python findheap.py <ram.bin|state.p2s> [known_good_hex]
"""
import struct
import sys
import zipfile

RAM = 32 * 1024 * 1024
MASK = 0x1FFFFFFE


def load(path):
    if path.lower().endswith('.p2s'):
        with zipfile.ZipFile(path) as z:
            d = z.read('eeMemory.bin')
    else:
        with open(path, 'rb') as f:
            d = f.read()
    if len(d) < RAM:
        raise SystemExit('short image')
    return d


def sz(d, c):
    return struct.unpack_from('<Q', d, c + 8)[0] & MASK


def walk_from(d, base, stop=RAM):
    """walk up; return (#chunks, end_addr, status)"""
    c = base
    n = 0
    while c + 16 <= RAM:
        s = sz(d, c)
        if s < 32 or (s & 0xF) or c + s > RAM:
            return n, c, 'invalid@0x%08X size=0x%X' % (c, s)
        n += 1
        c += s
        if c == stop:
            return n, c, 'hit-stop'
        if n > 400000:
            return n, c, 'runaway'
    return n, c, 'end-of-ram'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    d = load(sys.argv[1])
    stop = int(sys.argv[2], 16) if len(sys.argv) > 2 else RAM
    best = []
    # coarse sweep on 0x1000 then refine
    for step, rng in ((0x1000, range(0x00400000, 0x01200000, 0x1000)),):
        for b in rng:
            n, end, st = walk_from(d, b, stop)
            if st in ('hit-stop',) and n >= 8:
                best.append((b, n))
    print('candidates (base, nchunks) that walk cleanly to 0x%08X:' % stop)
    for b, n in best[:40]:
        print('   0x%08X  %d chunks' % (b, n))
    if best:
        lo = min(b for b, _ in best)
        # refine downward in 16-byte steps from lo+0x1000
        fine = []
        for b in range(lo, lo + 0x1000, 16):
            n, end, st = walk_from(d, b, stop)
            if st == 'hit-stop' and n >= 8:
                fine.append((b, n))
        if fine:
            print('finest base: 0x%08X (%d chunks)' % fine[0])
            b, n = fine[0]
            print('chunk list:')
            c = b
            tot = 0
            for i in range(min(n, 40)):
                s = sz(d, c)
                nx = c + s
                pin = struct.unpack_from('<Q', d, nx + 8)[0] & 1
                print('   [%02d] chunk=0x%08X size=0x%08X (%8d) next_PREV_INUSE=%d %s' %
                      (i, c, s, s, pin, 'INUSE' if pin else 'FREE'))
                c = nx
                tot += 1
            print('   ... total %d chunks' % n)


if __name__ == '__main__':
    main()
