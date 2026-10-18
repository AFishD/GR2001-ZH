# -*- coding: utf-8 -*-
r"""validate_base.py -- pick the heap base by requiring that every free chunk
referenced from the allocator's bin array lands exactly on a chunk start of the
linear walk, then produce the full accounting.

usage: python validate_base.py <ram.bin|state.p2s> [top_hex]
"""
import struct
import sys
import zipfile

RAM = 32 * 1024 * 1024
MASK = 0x1FFFFFFE
MSTATE = 0x0055B7A0          # arg a0 of core alloc, see hook a0=0055B7A0
BINS_BASE = 0x0055B7A8       # fd of bin 0; fake_chunk(i) = MSTATE - 8 + 8*i
BIN_END = 0x0055BBA8
SENT0 = 0x0055B798           # fake chunk address of bin 0
TOP = 0x01B0ED20


def load(path):
    if path.lower().endswith('.p2s'):
        with zipfile.ZipFile(path) as z:
            return z.read('eeMemory.bin')
    return open(path, 'rb').read()


def size_of(d, c):
    return struct.unpack_from('<Q', d, c + 8)[0] & MASK


def bin_refs(d):
    """all chunk addresses referenced from the bin array, with their bin index"""
    refs = {}
    i = 0
    a = BINS_BASE
    while a < BIN_END:
        fd = struct.unpack_from('<I', d, a)[0]
        bk = struct.unpack_from('<I', d, a + 4)[0]
        sent = SENT0 + 8 * i
        for v in (fd, bk):
            if 0x5E0000 < v < 0x01F98020:   # heap range only (exclude static sentinels)
                refs.setdefault(v, []).append((i, 'fd' if v == fd else 'bk', sent))
        i += 1
        a += 8
    return refs


def walk(d, base, stop):
    starts = []
    c = base
    if base < 0x400000:
        return None
    # the chunk just below base must NOT chain into base (else base is not the start)
    while c + 16 <= RAM:
        s = size_of(d, c)
        if s < 32 or (s & 0xF) or c + s > RAM:
            return starts, c, 'invalid@0x%08X size=0x%X' % (c, s)
        starts.append(c)
        c += s
        if c == stop:
            return starts, c, 'hit-stop'
        if len(starts) > 300000:
            return starts, c, 'runaway'
    return starts, c, 'end'


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    d = load(sys.argv[1])
    stop = int(sys.argv[2], 16) if len(sys.argv) > 2 else TOP
    refs = bin_refs(d)
    print('bin array 0x%08X..0x%08X: %d distinct chunk addrs referenced' % (BINS_BASE, BIN_END, len(refs)))
    cands = []
    for b in range(0x005E0000, 0x00A00000, 0x10):
        r = walk(d, b, stop)
        if not r:
            continue
        starts, end, st = r
        if st != 'hit-stop':
            continue
        ss = set(starts)
        missing = [v for v in refs if v not in ss]
        prev = size_of(d, b - 16) if b >= 16 else 0
        cands.append((len(missing), b, len(starts), prev))
    cands.sort()
    print('best candidate bases (missing_refs, base, nchunks, size_of_chunk_below):')
    for m, b, n, prev in cands[:8]:
        print('   missing=%d base=0x%08X chunks=%d prev_size(0x%08X)=0x%X' % (m, b, n, b - 16, prev))


if __name__ == '__main__':
    main()
