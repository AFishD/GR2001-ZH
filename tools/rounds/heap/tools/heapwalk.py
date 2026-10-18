# -*- coding: utf-8 -*-
r"""heapwalk.py -- offline dlmalloc heap accounting for Ghost Recon (PS2) EE RAM.

Chunk layout (derived from disassembly, see evidence\dis_*.txt):
  chunk+0x00 : prev_foot   (8 bytes)
  chunk+0x08 : head        (8 bytes, LE);  size = head & 0x1FFFFFFE  (bit0 = PREV_INUSE)
  chunk+0x10 : fd          (4 bytes, free chunks only)
  chunk+0x14 : bk          (4 bytes, free chunks only)
  mem        = chunk + 0x10
  next       = chunk + size

Bin array (free-list sentinels): starts at 0x0055B7B0 in this build; bin i's fake
chunk address is BINS_BASE - 0x10 + 0x8*i, so its fd/bk live at BINS_BASE + 8*i.

usage:
  python heapwalk.py scan  <ram.bin|state.p2s>
  python heapwalk.py walk  <ram.bin|state.p2s> <base_hex> <top_hex>
  python heapwalk.py timeseries <label=path> [label=path ...]
"""
import struct
import sys
import zipfile

RAM = 32 * 1024 * 1024
MSTATE = 0x0055B7A0
BINS_BASE = 0x0055B7B0
SIZE_MASK = 0x1FFFFFFE
FLAG_MASK = 0xFFFFFFFFE0000000
MIN_CHUNK = 32


def load(path):
    if path.lower().endswith('.p2s'):
        with zipfile.ZipFile(path) as z:
            d = z.read('eeMemory.bin')
    else:
        with open(path, 'rb') as f:
            d = f.read()
    if len(d) < RAM:
        raise SystemExit('short image: %d' % len(d))
    return d


def u32(d, a):
    return struct.unpack_from('<I', d, a)[0]


def u64(d, a):
    return struct.unpack_from('<Q', d, a)[0]


def head(d, c):
    return u64(d, c + 8)


def size_of(d, c):
    return head(d, c) & SIZE_MASK


def prev_inuse(d, c):
    return head(d, c) & 1


def valid_chunk(d, c, limit):
    """cheap plausibility test for a chunk header at c"""
    if c < 16 or c + 16 > RAM:
        return None
    s = size_of(d, c)
    if s < MIN_CHUNK or (s & 0xF):
        return None
    if c + s > limit:
        return None
    return s


def walk(d, base, top_hint=None):
    """linear walk from base; returns (chunks, status)."""
    chunks = []
    c = base
    limit = top_hint if top_hint else RAM
    while c < RAM - 16:
        s = valid_chunk(d, c, RAM)
        if s is None:
            return chunks, 'INVALID at 0x%08X (head=0x%016X)' % (c, head(d, c))
        nxt = c + s
        chunks.append(c)
        if top_hint and c == top_hint:
            return chunks, 'reached-top'
        if nxt == c:
            return chunks, 'zero-advance'
        c = nxt
        if len(chunks) > 400000:
            return chunks, 'runaway'
    return chunks, 'ran-off-end'


def bin_slots(d, lo=MSTATE, hi=0x0055D000):
    """all (addr,value) pointer slots in the mstate region that point into RAM"""
    out = []
    for a in range(lo, hi, 4):
        v = u32(d, a)
        if 0x1000 < v < RAM:
            out.append((a, v))
    return out


def freelist_chunks(d, hi=0x0055D000):
    """enumerate free chunks by following every plausible bin sentinel.
    A bin sentinel for bin i is the address S = BINS_BASE - 0x10 + 8*i; the slot
    pair at BINS_BASE+8*i is (S.fd, S.bk); empty => both == S."""
    found = {}
    n = 0
    while True:
        s = BINS_BASE - 0x10 + 8 * n
        if s + 8 > hi:
            break
        fd = u32(d, BINS_BASE + 8 * n)
        bk = u32(d, BINS_BASE + 8 * n + 4)
        n += 1
        if fd == s and bk == s:
            continue
        # follow fd chain, guard against loops
        seen = set()
        p = fd
        while p != s and 0x1000 < p < RAM and p not in seen and len(seen) < 4096:
            seen.add(p)
            found[p] = n - 1
            p = u32(d, p + 16)
        if p != s:
            found.setdefault(('BROKEN', n - 1), (fd, bk, p))
    return found, n


def stats(d, chunks, top):
    used_n = used_b = free_n = free_b = 0
    free_sizes = []
    bad = []
    for c in chunks:
        s = size_of(d, c)
        if c == top:
            free_n += 1
            free_b += s
            free_sizes.append(s)
            continue
        # in-use iff the NEXT chunk's head has PREV_INUSE
        nxt = c + s
        flag = prev_inuse(d, nxt) if nxt + 16 <= RAM else 0
        if flag:
            used_n += 1
            used_b += s
        else:
            free_n += 1
            free_b += s
            free_sizes.append(s)
    return used_n, used_b, free_n, free_b, free_sizes


def report(d, name, base, top):
    chunks, status = walk(d, base, top)
    print('== %s' % name)
    print('   walk: %d chunks, status=%s' % (len(chunks), status))
    if not chunks:
        return
    u_n, u_b, f_n, f_b, fs = stats(d, chunks, top)
    tot = u_b + f_b
    print('   heap base=0x%08X  top=0x%08X  top_size=0x%X (%d)' % (base, top, size_of(d, top), size_of(d, top)))
    print('   heap end=0x%08X  total walk bytes=0x%X (%d = %.2f MB)' % (top + size_of(d, top), tot, tot, tot / 1048576.0))
    print('   used : %6d chunks  %10d B (%.2f MB)  %5.1f%%' % (u_n, u_b, u_b / 1048576.0, 100.0 * u_b / tot))
    print('   free : %6d chunks  %10d B (%.2f MB)  %5.1f%%' % (f_n, f_b, f_b / 1048576.0, 100.0 * f_b / tot))
    if fs:
        fs_sorted = sorted(fs, reverse=True)
        print('   largest free chunks: %s' % ', '.join('%d' % x for x in fs_sorted[:12]))
        ge = [x for x in fs if x >= 0x10020]
        print('   free chunks >= 0x10020 (65,568 B): %d (total %d B)' % (len(ge), sum(ge)))
    # cross-check free chunks against the bin lists
    fl, nbins = freelist_chunks(d)
    print('   bins scanned: %d ; chunks reachable from bins: %d' % (nbins, len([k for k in fl if not isinstance(k, tuple)])))
    return chunks


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode = sys.argv[1]
    if mode == 'scan':
        d = load(sys.argv[2])
        print('mstate 0x%08X .. 0x%08X:' % (MSTATE, 0x0055C200))
        for a, v in bin_slots(d):
            print('   0x%08X = 0x%08X' % (a, v))
    elif mode == 'walk':
        d = load(sys.argv[2])
        base = int(sys.argv[3], 16)
        top = int(sys.argv[4], 16)
        report(d, sys.argv[2], base, top)
    elif mode == 'findbase':
        d = load(sys.argv[2])
        top = int(sys.argv[3], 16)
        # candidate bases: try to walk down; use min free chunk then extend downward
        best = None
        cands = []
        for v in range(0x00400000, 0x01200000, 0x10000):
            cands.append(v)
        for b in cands:
            chunks, status = walk(d, b, top)
            if status == 'reached-top' and len(chunks) > 3:
                # check the chunk *before* b is invalid or b is the true base
                if best is None or b < best:
                    best = b
        print('lowest base that walks cleanly to top: %s' % ('0x%08X' % best if best else 'NONE'))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
