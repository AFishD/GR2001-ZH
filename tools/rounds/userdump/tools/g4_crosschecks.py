# -*- coding: utf-8 -*-
"""G4: cross-checks for the user-dump analysis.

1) low RAM 0x0..0x400 (EE exception-vector page) in both dumps
2) full arena walk from base 0x0065AEA0 (per REPORT_HEAP_EXHAUSTION) + free-chunk <-> bin accounting
3) every bucket entry checked as a *pointer* (in-RAM, 8-aligned) -> list of out-of-range entries
4) watch_00500000_00581000.bin cross-check against ee_ram.bin
5) who writes 0x55B7A0..0x55C000 at all: allocator-only?  (both rings)
"""
import os, struct
from collections import Counter, defaultdict

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
DUMPS = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\hookdumps")
OUT = os.path.join(ROOT, r"work\builds\GR_USERDUMP\out")
MSTATE = 0x0055B7A0
BB = 0x0055B7A8
BE = BB + 128 * 8
HEAP_BASE = 0x0065AEA0
RAM = 0x02000000

def pseudo(i):
    return 0x0055B798 + 8 * i

def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]

def u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]

L = []
A = L.append

for tag, dn in (("OLD f19701", "hook_19701_hotkey_f10"), ("NEW f23444", "hook_23444_hotkey_f10")):
    d = os.path.join(DUMPS, dn)
    ram = open(os.path.join(d, "ee_ram.bin"), "rb").read()
    A("=" * 110)
    A("%s   %s" % (tag, dn))
    A("=" * 110)

    # 1) low RAM / exception vector page
    A("")
    A("[1] low RAM 0x0000..0x0400 (EE exception vectors) - first 0x80 bytes:")
    for b in range(0, 0x80, 16):
        A("    0x%04X: %s" % (b, " ".join("%02X" % c for c in ram[b:b + 16])))
    nz = sum(1 for c in ram[0:0x400] if c)
    A("    non-zero bytes in 0x0..0x400: %d / 1024" % nz)
    A("    words 0x00/0x04/0x08/0x0C/0x10/0x14: %s"
      % " ".join("%08X" % u32(ram, o) for o in (0, 4, 8, 0xC, 0x10, 0x14)))

    # 2) arena walk from base
    A("")
    A("[2] arena walk from base 0x%08X" % HEAP_BASE)
    off = HEAP_BASE
    chunks = []
    while off + 16 <= RAM:
        head = u64(ram, off + 8)
        size = head & 0x1FFFFFFE
        pinuse = head & 1
        if size < 16 or (off + size) > RAM:
            A("    STOP at 0x%08X head=0x%016X size=0x%X (invalid)" % (off, head, size))
            break
        chunks.append((off, size, pinuse, head))
        off += size
    A("    chunks=%d  heap_end=0x%08X  (arena bytes=0x%X)" % (len(chunks), off, off - HEAP_BASE))
    free = [c for c in chunks if c[2] == 0 and c[0] != HEAP_BASE]
    A("    chunks with prev_inuse=0 (i.e. previous chunk is free) = %d" % len(free))
    # free chunks = those whose *own* next head has prev_inuse=0
    freereal = []
    for idx, (o, s, p, h) in enumerate(chunks):
        nxt = o + s
        if nxt + 16 <= RAM:
            nh = u64(ram, nxt + 8)
            if (nh & 1) == 0:
                freereal.append((o, s))
    A("    chunks that ARE free (next chunk head has prev_inuse=0) = %d" % len(freereal))
    A("    first 20 free chunks: %s" % ", ".join("0x%08X(%d)" % (o, s) for o, s in freereal[:20]))

    # 3) bucket entries as pointers
    A("")
    A("[3] bucket-entry pointer sanity (all values must be inside EE RAM, 8-aligned, or the bin pseudo):")
    bad = []
    for i in range(128):
        fd = u32(ram, BB + 8 * i)
        bk = u32(ram, BB + 8 * i + 4)
        for nm, v in (("fd", fd), ("bk", bk)):
            if v == pseudo(i):
                continue
            if i == 0:
                continue
            if not (HEAP_BASE <= v < RAM) or (v % 8):
                bad.append((i, nm, v, BB + 8 * i + (0 if nm == "fd" else 4)))
    A("    out-of-range / misaligned bucket entries: %d" % len(bad))
    for (i, nm, v, slot) in bad:
        A("      bucket %3d %s = 0x%08X   (slot 0x%08X)  pseudo=0x%08X" % (i, nm, v, slot, pseudo(i)))
    # how many bins are empty vs non-empty
    empt = sum(1 for i in range(1, 128) if u32(ram, BB + 8 * i) == pseudo(i) and u32(ram, BB + 8 * i + 4) == pseudo(i))
    A("    empty bins (fd==bk==pseudo), idx 1..127: %d" % empt)

    # cross-check: are all bucket chunk pointers valid chunk starts in the walk?
    A("")
    A("[3b] do bucket entries point at real chunk boundaries of the walk?")
    starts = set(o for (o, s, p, h) in chunks)
    miss = []
    for i in range(1, 128):
        for nm, v in (("fd", u32(ram, BB + 8 * i)), ("bk", u32(ram, BB + 8 * i + 4))):
            if v == pseudo(i):
                continue
            if v not in starts:
                miss.append((i, nm, v))
    A("    entries NOT equal to any chunk start: %d" % len(miss))
    for (i, nm, v) in miss[:40]:
        A("      bucket %3d %s = 0x%08X" % (i, nm, v))

    # 4) watch snapshot cross-check
    w = os.path.join(d, "watch_00500000_00581000.bin")
    if os.path.exists(w):
        wb = open(w, "rb").read()
        base = 0x00500000
        ok = all(wb[o - base] == ram[o] for o in (MSTATE, BB, 0x55BB98, 0x55BB9C, BE - 4))
        A("")
        A("[4] watch_00500000_00581000.bin == ee_ram for mstate/bin126/bin_end: %s" % ok)
        A("    watch[0x55BB98-0x500000] (bin126 fd) = 0x%08X"
          % u32(wb, 0x55BB98 - base))
        A("    watch[0x55BB9C-0x500000] (bin126 bk) = 0x%08X"
          % u32(wb, 0x55BB9C - base))

    # 5) top 0x0065AEA0..0x0065B000 header
    A("")
    A("[5] arena header 0x%08X..0x%08X:" % (HEAP_BASE, HEAP_BASE + 0x40))
    for b in range(0, 0x40, 8):
        A("    0x%08X: %016X" % (HEAP_BASE + b, u64(ram, HEAP_BASE + b)))
    A("")

# 5) which PCs ever write 0x55B7A0..0x55C000 (both rings)
def parse_ring(path):
    b = open(path, "rb").read()
    for i in range(len(b) // 24):
        o = i * 24
        fr, pc, ad = struct.unpack_from("<III", b, o)
        val = struct.unpack_from("<Q", b, o + 12)[0]
        size, pad, dr, src = b[o + 20], b[o + 21], b[o + 22], b[o + 23]
        yield (i, fr, pc, ad, size, dr, src, val)

A("=" * 110)
A("[6] every PC that writes anywhere in 0x55B7A0..0x55C000 (mstate + whole bin array + pad), both rings")
A("=" * 110)
for tag, dn in (("OLD f19701", "hook_19701_hotkey_f10"), ("NEW f23444", "hook_23444_hotkey_f10")):
    c = Counter()
    lo = 0xFFFFFFFF
    hi = 0
    for (i, fr, pc, ad, size, dr, src, val) in parse_ring(os.path.join(DUMPS, dn, "ring.bin")):
        w = max(1, size // 8)
        if ad < 0x55C000 and ad + w > 0x55B7A0:
            c["%08X" % pc] += 1
            lo = min(lo, ad)
            hi = max(hi, ad + w)
    A("")
    A("%s : addr range touched 0x%08X..0x%08X ; %d distinct PCs" % (tag, lo, hi, len(c)))
    outside = [p for p in c if not (0x101C00 <= int(p, 16) <= 0x102700)]
    A("    PCs OUTSIDE the allocator image 0x00101C00..0x00102700 : %s" % (outside or "NONE"))
    for p, n in c.most_common(40):
        A("      %s x%d" % (p, n))

open(os.path.join(OUT, "g4_crosschecks.txt"), "w", encoding="utf-8").write("\n".join(L))
print("written g4_crosschecks.txt  lines=%d" % len(L))
