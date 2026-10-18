# -*- coding: utf-8 -*-
"""findblob.py -- locate a byte pattern (a compressed resource stream taken out of an
EE RAM dump) inside an ISO/raw image, and map the hit offset to an ISO9660 file.

READ-ONLY.

usage:
  python findblob.py <image> <pattern_hexfile> [maxhits]
  python findblob.py --dump <eeram.bin> <addr> <len> <out.bin>   extract the pattern
  python findblob.py --iso <image> <lba> <nbytes>                list dir records of a dir
"""
import struct
import sys

SECTOR = 2048


def dump(eeram, addr, ln, out):
    with open(eeram, 'rb') as f:
        f.seek(addr)
        d = f.read(ln)
    with open(out, 'wb') as f:
        f.write(d)
    print('wrote %d bytes from %s@0x%X to %s' % (len(d), eeram, addr, out))


def read_dir(img, lba, size):
    """parse an ISO9660 directory, return [(name, lba, size, is_dir)]"""
    with open(img, 'rb') as f:
        f.seek(lba * SECTOR)
        d = f.read(size)
    out = []
    off = 0
    while off < len(d):
        rl = d[off]
        if rl == 0:
            off = ((off // SECTOR) + 1) * SECTOR
            if off >= len(d):
                break
            continue
        rec = d[off:off + rl]
        ext_lba = struct.unpack_from('<I', rec, 2)[0]
        ext_size = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        nlen = rec[32]
        name = rec[33:33 + nlen]
        nm = name.decode('latin-1')
        if nm in ('\x00', '\x01'):
            nm = '.' if nm == '\x00' else '..'
        else:
            nm = nm.split(';')[0]
        out.append((nm, ext_lba, ext_size, bool(flags & 2)))
        off += rl
    return out


def walk(img, lba, size, prefix, depth=0, acc=None):
    if acc is None:
        acc = []
    for (nm, l, sz, isdir) in read_dir(img, lba, size):
        if nm in ('.', '..'):
            continue
        acc.append((prefix + '/' + nm, l, sz, isdir))
        if isdir and depth < 6:
            walk(img, l, sz, prefix + '/' + nm, depth + 1, acc)
    return acc


def find(img, pat, maxhits=8):
    n = len(pat)
    first = pat[:64]
    hits = []
    CH = 4 << 20
    with open(img, 'rb') as f:
        base = 0
        tail = b''
        while len(hits) < maxhits:
            chunk = f.read(CH)
            if not chunk:
                break
            buf = tail + chunk
            start = 0
            while True:
                j = buf.find(first, start)
                if j < 0:
                    break
                if buf[j:j + n] == pat:
                    hits.append(base - len(tail) + j)
                    if len(hits) >= maxhits:
                        break
                start = j + 1
            tail = buf[-(n - 1):] if n > 1 else b''
            base += len(chunk)
    return hits


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if sys.argv[1] == '--dump':
        dump(sys.argv[2], int(sys.argv[3], 16), int(sys.argv[4], 16), sys.argv[5])
        return
    if sys.argv[1] == '--iso':
        img = sys.argv[2]
        lba = int(sys.argv[3])
        n = int(sys.argv[4])
        for r in read_dir(img, lba, n):
            print('   %-32s lba=%-8d size=%-10d %s' % (r[0], r[1], r[2], 'DIR' if r[3] else ''))
        return
    if sys.argv[1] == '--walk':
        img = sys.argv[2]
        pvd = open(img, 'rb').read(32 * SECTOR)
        root = pvd[156:156 + 34]
        rlba = struct.unpack_from('<I', root, 2)[0]
        rsz = struct.unpack_from('<I', root, 10)[0]
        print('root dir lba=%d size=%d' % (rlba, rsz))
        for e in walk(img, rlba, rsz, ''):
            print('   %-60s lba=%-8d size=%-10d %s' % (e[0], e[1], e[2], 'DIR' if e[3] else ''))
        return
    img = sys.argv[1]
    with open(sys.argv[2], 'rb') as f:
        pat = f.read()
    mh = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    print('pattern %d bytes, first16=%s' % (len(pat), pat[:16].hex()))
    hits = find(img, pat, mh)
    print('hits in %s: %d' % (img, len(hits)))
    for h in hits:
        print('   file offset 0x%X (%d)  lba %.3f  sector %d +0x%X' %
              (h, h, h / SECTOR, h // SECTOR, h % SECTOR))


if __name__ == '__main__':
    main()
