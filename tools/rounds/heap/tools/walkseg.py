# -*- coding: utf-8 -*-
r"""walkseg.py -- print the chunk headers from a start address upward, flagging
whether each head carries the allocator fingerprint (upper 32 bits 0xFFFFFFFF).

usage: python walkseg.py <ram> <start_hex> <count>
"""
import struct
import sys
import zipfile

MASK = 0x1FFFFFFE


def load(path):
    if path.lower().endswith('.p2s'):
        with zipfile.ZipFile(path) as z:
            return z.read('eeMemory.bin')
    return open(path, 'rb').read()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    d = load(sys.argv[1])
    c = int(sys.argv[2], 16)
    n = int(sys.argv[3], 0)
    for i in range(n):
        h = struct.unpack_from('<Q', d, c + 8)[0]
        pf = struct.unpack_from('<Q', d, c)[0]
        s = h & MASK
        fp = 'FP' if (h >> 32) == 0xFFFFFFFF else '--'
        fd, bk = struct.unpack_from('<II', d, c + 16)
        print('  [%3d] 0x%08X head=0x%016X %s size=0x%08X(%9d) prev_foot=0x%016X fd=0x%08X bk=0x%08X'
              % (i, c, h, fp, s, s, pf, fd, bk))
        if s < 32 or (s & 0xF) or c + s > len(d):
            print('       -> invalid, stop')
            break
        c += s


if __name__ == '__main__':
    main()
