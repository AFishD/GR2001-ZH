# -*- coding: utf-8 -*-
"""G1: allocator mstate / bucket-array forensics for the two user dumps.

Definitions taken verbatim from docs\\REPORT_HEAP_EXHAUSTION.md:
  mstate              = 0x0055B7A0
    +0x00              = ? (flags/counters)
    +0x08 (0x55B7A8)   = heap top (wilderness) chunk ptr  [also alias of bucket-0 fd]
    +0x0C (0x55B7AC)   = constant 0x0055B798             [also alias of bucket-0 bk]
  bucket array starts 0x0055B7A8, 8 B per bucket (fd,bk)
  bucket i pseudo-chunk = 0x0055B798 + 8*i
      fd at 0x0055B7A8 + 8*i  ( = pseudo + 0x10 )
      bk at 0x0055B7AC + 8*i  ( = pseudo + 0x14 )
  empty bucket i  <=>  fd == bk == (0x0055B798 + 8*i)
  bucket 126 slots: fd @ 0x0055BB98, bk @ 0x0055BB9C ; healthy value 0x0055BB88
"""
import os, sys, struct, hashlib, json

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
DUMPS = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\hookdumps")
OUT = os.path.join(ROOT, r"work\builds\GR_USERDUMP\out")

MSTATE = 0x0055B7A0
CONST_55B798 = 0x0055B798
BUCKETS = 128
BUCKET_BASE = 0x0055B7A8          # == MSTATE + 8
BUCKET_BYTES = BUCKETS * 8

def u32(b, off):
    return struct.unpack_from("<I", b, off)[0]

def pseudo(i):
    return CONST_55B798 + 8 * i

def analyze(tag, dirname):
    d = os.path.join(DUMPS, dirname)
    ram = open(os.path.join(d, "ee_ram.bin"), "rb").read()
    assert len(ram) == 32 * 1024 * 1024, len(ram)

    lines = []
    lines.append("=" * 100)
    lines.append("DUMP %s  (%s)" % (tag, dirname))
    lines.append("=" * 100)
    lines.append("ee_ram.bin sha256 = %s" % hashlib.sha256(ram).hexdigest())

    # --- mstate header ---
    lines.append("")
    lines.append("--- mstate 0x%08X .. 0x%08X ---" % (MSTATE, MSTATE + 0x20))
    for off in range(0, 0x20, 4):
        lines.append("  [0x%08X] = 0x%08X" % (MSTATE + off, u32(ram, MSTATE + off)))
    lines.append("  note: +0x08 must be heap-top chunk ptr, +0x0C must be 0x0055B798")

    # --- bucket self-reference audit ---
    broken = []
    lines.append("")
    lines.append("--- bucket array 0x%08X .. 0x%08X (128 buckets x 8 B) ---" % (BUCKET_BASE, BUCKET_BASE + BUCKET_BYTES))
    lines.append("  %-4s %-10s %-10s %-10s %-10s %-10s %s" % ("idx", "pseudo", "fd@+0", "bk@+4", "fd_slot", "bk_slot", "state"))
    for i in range(BUCKETS):
        fd = u32(ram, BUCKET_BASE + 8 * i)
        bk = u32(ram, BUCKET_BASE + 8 * i + 4)
        ps = pseudo(i)
        ok = (fd == ps and bk == ps)
        # bucket 0 is aliased by top / const, never used by the allocator
        alias0 = (i == 0)
        state = "EMPTY-SELFREF" if ok else ("ALIAS(bucket0:top/const)" if alias0 else "**BROKEN**")
        if not ok and not alias0:
            broken.append((i, ps, fd, bk))
        if (not ok) or i in (0, 4, 6, 30, 56, 77, 110, 125, 126, 127):
            lines.append("  %-4d 0x%08X 0x%08X 0x%08X 0x%08X 0x%08X %s"
                         % (i, ps, fd, bk, BUCKET_BASE + 8 * i, BUCKET_BASE + 8 * i + 4, state))
    lines.append("")
    lines.append("  broken (non-self-referential, excluding idx 0 alias): %d" % len(broken))
    for (i, ps, fd, bk) in broken:
        lines.append("    idx=%3d pseudo=0x%08X fd=0x%08X bk=0x%08X  (fd_slot=0x%08X bk_slot=0x%08X)"
                     % (i, ps, fd, bk, BUCKET_BASE + 8 * i, BUCKET_BASE + 8 * i + 4))

    # --- bucket 126 spotlight ---
    b126 = (u32(ram, 0x0055BB98), u32(ram, 0x0055BB9C))
    lines.append("")
    lines.append("--- BUCKET 126 (pseudo=0x%08X) ---" % pseudo(126))
    lines.append("  0x0055BB98 (fd) = 0x%08X" % b126[0])
    lines.append("  0x0055BB9C (bk) = 0x%08X" % b126[1])
    verdict = "HEALTHY (self-referential 0x%08X)" % pseudo(126) if b126 == (pseudo(126), pseudo(126)) \
              else "**CORRUPT**"
    lines.append("  verdict: %s" % verdict)

    # --- raw byte window around bucket 126 ---
    lines.append("")
    lines.append("  raw bytes 0x0055BB80..0x0055BBA8:")
    for base in range(0x0055BB80, 0x0055BBA8, 16):
        lines.append("    0x%08X: %s" % (base, " ".join("%02X" % c for c in ram[base:base + 16])))

    # --- whole-RAM uniqueness scan for the corrupt value ---
    rv = []
    for v in set([b126[0], b126[1]]):
        if v == pseudo(126):
            continue
        pat = struct.pack("<I", v)
        hits = []
        start = 0
        while True:
            j = ram.find(pat, start)
            if j < 0:
                break
            hits.append(j)
            start = j + 1
        lines.append("")
        lines.append("  whole-RAM occurrences of 0x%08X (4-byte, little-endian, overlapping): %d" % (v, len(hits)))
        for h in hits[:24]:
            lines.append("    @0x%08X" % h)
        if len(hits) > 24:
            lines.append("    ... (%d more)" % (len(hits) - 24))
        rv.append((v, len(hits), hits))

    # --- heap walk (per REPORT_HEAP_EXHAUSTION chunk layout) ---
    top = u32(ram, MSTATE + 8)
    lines.append("")
    lines.append("--- heap walk from top ptr 0x%08X ---" % top)
    try:
        walk_heap(ram, top, lines)
    except Exception as e:
        lines.append("  heap walk failed: %r" % (e,))

    lines.append("")
    return "\n".join(lines), b126, broken, top

def walk_heap(ram, top, lines, limit=400000):
    """chunk = prev_foot(8) + head(8, size = head & 0x1FFFFFFE) + payload"""
    off = top
    n = 0
    free_found = []
    while off + 16 <= len(ram) and n < limit:
        head = struct.unpack_from("<Q", ram, off + 8)[0]
        size = head & 0x1FFFFFFE
        prev_inuse = head & 1
        if size < 16 or (off + size) > len(ram):
            lines.append("  [%6d] 0x%08X head=0x%016X size=0x%X prev_inuse=%d  <-- STOP (invalid)"
                         % (n, off, head, size, prev_inuse))
            break
        if not prev_inuse:
            free_found.append(off)
        lines.append("  [%6d] 0x%08X head=0x%016X size=%-9d(0x%X) prev_inuse=%d"
                     % (n, off, head, size, size, prev_inuse))
        off += size
        n += 1
    lines.append("  walked %d chunks, %d of them marked free (prev_inuse=0)" % (n, len(free_found)))
    lines.append("  heap_end after last chunk = 0x%08X" % off)

def main():
    os.makedirs(OUT, exist_ok=True)
    res = {}
    allout = []
    for tag, dn in (("OLD (frame 19701)", "hook_19701_hotkey_f10"),
                    ("NEW (frame 23444)", "hook_23444_hotkey_f10")):
        txt, b126, broken, top = analyze(tag, dn)
        allout.append(txt)
        key = "old" if "19701" in dn else "new"
        res[key] = dict(dir=dn, b126=[b126[0], b126[1]], broken=broken, top=top)
    with open(os.path.join(OUT, "g1_buckets.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(allout))
    with open(os.path.join(OUT, "g1_buckets.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    # concise stdout
    for k in ("old", "new"):
        r = res[k]
        print("%s %s  bucket126 fd=0x%08X bk=0x%08X  top=0x%08X  broken_buckets=%s"
              % (k, r["dir"], r["b126"][0], r["b126"][1], r["top"],
                 [(i, hex(f), hex(b)) for (i, p, f, b) in r["broken"]]))

if __name__ == "__main__":
    main()
