# -*- coding: utf-8 -*-
r"""heapaudit.py -- offline heap accounting + free-list integrity audit for the
Ghost Recon (PS2, SLUS-20613) dlmalloc variant, straight out of an EE RAM image.

Layout proven from disassembly + live hook registers (see evidence\*.txt):
  mstate                 0x0055B7A0   (arg a0 of core alloc 0x00102050; hook shows a0=0055B7A0)
    +0x00 u64 binmap
    +0x08 u32 top         (hook/empirical: pointer to the wilderness chunk)
    +0x0C u32 const       0x0055B798 in every state inspected
    +0x10 .. bin (fd,bk) pairs, 127 of them; bin i fake chunk = 0x0055B798 + 8*i
  chunk: +0x00 prev_foot(8) +0x08 head(8, size = head & 0x1FFFFFFE) +0x10 fd(4) +0x14 bk(4)
  mem = chunk + 0x10 ; usable = size - 8 (next chunk's prev_foot is usable)

usage: python heapaudit.py <ram.bin|state.p2s> [label]
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RAM = 32 * 1024 * 1024
MASK = 0x1FFFFFFE
MSTATE = 0x0055B7A0
TOP_FIELD = MSTATE + 8
FIELDC = MSTATE + 12
BIN0 = MSTATE + 8          # bins[0].fd slot
NBINS = 127
SENT0 = MSTATE - 8         # 0x0055B798
HEAP_LO = 0x005E0000
HEAP_HI = 0x02000000


def load(path):
    if path.lower().endswith(('.p2s', '.backup')):
        import p2s
        return p2s.ee_ram(path)
    return open(path, 'rb').read()


def u32(d, a):
    return struct.unpack_from('<I', d, a)[0]


def u64(d, a):
    return struct.unpack_from('<Q', d, a)[0]


def size_of(d, c):
    return u64(d, c + 8) & MASK


def head_of(d, c):
    return u64(d, c + 8)


def find_base(d, top):
    """smallest 16-aligned address whose chunk chain runs into the top chunk"""
    end_expected = 0
    best = None
    for b in range(HEAP_LO, 0x00800000, 16):
        h = head_of(d, b)
        if (h >> 32) != 0xFFFFFFFF:
            continue
        s = h & MASK
        if s < 32 or (s & 0xF) or b + s > RAM:
            continue
        # try to chain
        c = b
        n = 0
        ok = True
        while n < 300000:
            s = size_of(d, c)
            if s < 32 or (s & 0xF) or c + s > RAM:
                ok = False
                break
            if c == top:
                break
            c += s
            n += 1
        if ok and c == top:
            best = (b, b)
            break
    return best[0] if best else None


def audit(d, label, base, top):
    out = {'label': label}
    top_sz = size_of(d, top)
    heap_end = top + top_sz
    # ---- linear walk
    starts = []
    c = base
    seq = []
    while c < heap_end:
        s = size_of(d, c)
        if s < 32 or (s & 0xF):
            out['walk_error'] = 'invalid chunk at 0x%08X size=0x%X' % (c, s)
            break
        seq.append(c)
        nx = c + s
        if nx == heap_end:
            break
        c = nx
    chunks = seq
    starts = set(chunks)
    used_n = used_b = free_n = free_b = 0
    free_sizes = []
    for i, c in enumerate(chunks):
        s = size_of(d, c)
        nx = c + s
        if nx >= heap_end:
            free_n += 1
            free_b += s
            free_sizes.append((s, c))
            continue
        pin = head_of(d, nx) & 1
        if pin:
            used_n += 1
            used_b += s
        else:
            free_n += 1
            free_b += s
            free_sizes.append((s, c))
    tot = used_b + free_b
    out.update({
        'heap_base': '0x%08X' % base,
        'top_ptr': '0x%08X' % top,
        'top_size': top_sz,
        'heap_end': '0x%08X' % heap_end,
        'heap_total': tot,
        'heap_total_mb': round(tot / 1048576.0, 2),
        'chunks_total': len(chunks),
        'used_chunks': used_n,
        'used_bytes': used_b,
        'used_pct': round(100.0 * used_b / tot, 2),
        'free_chunks': free_n,
        'free_bytes': free_b,
        'free_pct': round(100.0 * free_b / tot, 2),
        'top_free': top_sz,
        'largest_free': [{'size': s, 'at': '0x%08X' % a} for s, a in sorted(free_sizes, reverse=True)[:10]],
        'free_ge_65568': sorted([s for s, _ in free_sizes if s >= 0x10020], reverse=True),
    })
    # ---- bin integrity
    bins = []
    broken = 0
    nulls = 0
    listed = {}
    for i in range(NBINS):
        a = BIN0 + 8 * i
        fd = u32(d, a)
        bk = u32(d, a + 4)
        sent = SENT0 + 8 * i
        if fd == sent and bk == sent:
            continue            # empty bin, consistent
        entry = {'bin': i, 'fd': '0x%08X' % fd, 'bk': '0x%08X' % bk,
                 'sentinel': '0x%08X' % sent, 'problems': []}
        if fd == 0:
            entry['problems'].append('fd==NULL')
            nulls += 1
        if bk == 0:
            entry['problems'].append('bk==NULL')
            nulls += 1
        # walk the fd chain
        p = fd
        seen = []
        while p != sent and len(seen) < 5000:
            if p == 0 or not (HEAP_LO <= p < HEAP_HI):
                entry['problems'].append('chain left heap: 0x%08X' % p)
                break
            if p not in starts:
                entry['problems'].append('0x%08X is not a chunk start' % p)
            if u32(d, p + 20) != (seen[-1] if seen else sent):
                entry['problems'].append('0x%08X bk mismatch' % p)
            seen.append(p)
            listed[p] = i
            p = u32(d, p + 16)
        if p != sent:
            entry['problems'].append('fd chain did not close on sentinel (ended 0x%08X)' % p)
        if bk != (seen[-1] if seen else sent):
            entry['problems'].append('bin bk (0x%08X) != last chain element' % bk)
        if entry['problems']:
            broken += 1
        entry['nchunks'] = len(seen)
        bins.append(entry)
    # free-by-PREV_INUSE chunks that are not in any bin (and not the top)
    orphan = [c for c in chunks if c not in listed and c != chunks[-1]
              and (head_of(d, c + size_of(d, c)) & 1) == 0]
    out['bins_nonempty'] = len(bins)
    out['bins_broken'] = broken
    out['bin_null_slots'] = nulls
    out['free_chunks_not_in_any_bin'] = len(orphan)
    out['orphan_sample'] = ['0x%08X (size 0x%X)' % (c, size_of(d, c)) for c in orphan[:10]]
    out['bin_detail'] = bins
    out['binmap_u64'] = '0x%016X' % u64(d, MSTATE)
    out['field_0C'] = '0x%08X' % u32(d, FIELDC)
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    path = sys.argv[1]
    label = sys.argv[2] if len(sys.argv) > 2 else path
    forced = int(sys.argv[3], 16) if len(sys.argv) > 3 else None
    d = load(path)
    top = u32(d, TOP_FIELD)
    base = forced if forced else find_base(d, top)
    if base is None:
        print(json.dumps({'label': label, 'top_ptr': '0x%08X' % top,
                          'error': 'no base found that chains into top'}, ensure_ascii=False, indent=1))
        return
    out = audit(d, label, base, top)
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
