# -*- coding: utf-8 -*-
"""isodiff.py -- blocked comparison of two ISO images (READ-ONLY).

Reports differing 64 KiB blocks, coalesced into runs, and maps each run to the
ISO9660 file it falls in (root directory level).
"""
import struct
import sys

SECTOR = 2048
BLK = 64 * 1024


def root_entries(path):
    with open(path, 'rb') as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        rlba = struct.unpack_from('<I', pvd, 156 + 2)[0]
        rsz = struct.unpack_from('<I', pvd, 156 + 10)[0]
        f.seek(rlba * SECTOR)
        d = f.read(rsz)
    out = []
    off = 0
    while off < len(d):
        rl = d[off]
        if rl == 0:
            break
        nm = d[off + 33:off + 33 + d[off + 32]].decode('latin-1').split(';')[0]
        lba = struct.unpack_from('<I', d, off + 2)[0]
        sz = struct.unpack_from('<I', d, off + 10)[0]
        if nm not in ('\x00', '\x01'):
            out.append((nm, lba * SECTOR, sz))
        off += rl
    return out


def owner(ents, off):
    for (nm, o, sz) in ents:
        if o <= off < o + sz:
            return '%s+0x%X' % (nm, off - o)
    return '?'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    a_path, b_path = sys.argv[1], sys.argv[2]
    ents = root_entries(a_path)
    a = open(a_path, 'rb')
    b = open(b_path, 'rb')
    fa = a.seek(0, 2)
    fb = b.seek(0, 2)
    print('A=%s (%d bytes)' % (a_path, fa))
    print('B=%s (%d bytes)' % (b_path, fb))
    n = min(fa, fb)
    a.seek(0)
    b.seek(0)
    runs = []
    off = 0
    total_diff = 0
    while off < n:
        ca = a.read(BLK)
        cb = b.read(BLK)
        if ca != cb:
            total_diff += sum(1 for x, y in zip(ca, cb) if x != y)
            if runs and runs[-1][1] == off:
                runs[-1][1] = off + len(ca)
                runs[-1][2] += sum(1 for x, y in zip(ca, cb) if x != y)
            else:
                runs.append([off, off + len(ca), sum(1 for x, y in zip(ca, cb) if x != y)])
        off += BLK
    print('differing blocks: %d runs, %d differing bytes (of %d compared)' %
          (len(runs), total_diff, n))
    for (s, e, nd) in runs:
        print('   [0x%08X..0x%08X] %8d bytes differ   %s' % (s, e, nd, owner(ents, s)))
    if fa != fb:
        print('size differs by %d bytes; tail not compared' % (fb - fa))


if __name__ == '__main__':
    main()
