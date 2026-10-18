# -*- coding: utf-8 -*-
r"""heapmap.py -- map the allocator-managed region of EE RAM by chunk-header
fingerprint, then do full accounting.

Fingerprint: the allocator writes head = size | 0xFFFFFFFFE0000000 | flags
(see dis 0x0010223C-0x00102244, 0x00101E54-0x00101E68), i.e. the high 32 bits of
the 8-byte head word are always 0xFFFFFFFF for chunks it manages.
Game data that merely "looks like" a chunk does not carry that pattern.

usage:
  python heapmap.py map    <ram.bin|state.p2s>
  python heapmap.py stats  <ram.bin|state.p2s>
"""
import struct
import sys
import zipfile

RAM = 32 * 1024 * 1024
MASK = 0x1FFFFFFE
FP = 0xFFFFFFFF
LO = 0x00400000
HI = RAM


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


def heads(d):
    """dict addr -> (size, flags, upper) for fingerprint-matching chunk starts"""
    out = {}
    for a in range(LO, HI - 16, 16):
        h = struct.unpack_from('<Q', d, a + 8)[0]
        if (h >> 32) != FP:
            continue
        s = h & MASK
        if s < 32 or (s & 0xF) or a + s > HI:
            continue
        out[a] = (s, h & ~MASK)
    return out


def chains(hm):
    """maximal runs of chunks where next = a + size is itself a valid start"""
    out = []
    for a in sorted(hm):
        s = hm[a][0]
        nxt = a + s
        if nxt in hm:
            out.append((a, nxt))
    # only keep chain *links*; build runs
    nxtof = dict(out)
    starts = set(hm) - set(nxtof.values())
    runs = []
    for st in sorted(starts):
        cur = st
        n = 0
        end = st
        while cur in nxtof:
            n += 1
            cur = nxtof[cur]
            end = cur
        runs.append((st, end, n))
    return runs, nxtof


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    d = load(sys.argv[2])
    hm = heads(d)
    print('fingerprinted chunk starts: %d' % len(hm))
    runs, nxtof = chains(hm)
    runs.sort(key=lambda r: -r[2])
    print('runs (start, end, links):')
    for st, end, n in runs[:10]:
        print('   0x%08X -> 0x%08X  %d links  bytes=0x%X' % (st, end, n, end - st))
    if not runs:
        return
    st, end, n = runs[0]
    if sys.argv[1] == 'map':
        return
    # accounting over the longest run: walk it
    used_n = used_b = free_n = free_b = 0
    free_sizes = []
    c = st
    bad = 0
    while c in hm and c < end:
        s = hm[c][0]
        nx = c + s
        if nx == end:
            free_n += 1
            free_b += s
            free_sizes.append(s)
            break
        pin = struct.unpack_from('<Q', d, nx + 8)[0] & 1
        if pin:
            used_n += 1
            used_b += s
        else:
            free_n += 1
            free_b += s
            free_sizes.append(s)
        c = nx
    tot = used_b + free_b
    print('')
    print('HEAP RUN 0x%08X .. 0x%08X (0x%X bytes, %.2f MB)' % (st, end, end - st, (end - st) / 1048576.0))
    print('  chunks walked: used %d / free %d' % (used_n, free_n))
    print('  used bytes: %d (%.2f MB) %.1f%%' % (used_b, used_b / 1048576.0, 100.0 * used_b / tot))
    print('  free bytes: %d (%.2f MB) %.1f%%' % (free_b, free_b / 1048576.0, 100.0 * free_b / tot))
    print('  largest free chunks: %s' % ', '.join(str(x) for x in sorted(free_sizes, reverse=True)[:15]))


if __name__ == '__main__':
    main()
