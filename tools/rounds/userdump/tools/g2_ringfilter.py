# -*- coding: utf-8 -*-
"""G2: filter the HookWatch rings for stores into the allocator mstate + bucket array.

ring.bin record layout (24 B), little-endian, verified against ring.txt:
   +0x00 u32 frame
   +0x04 u32 pc
   +0x08 u32 addr
   +0x0C u64 value
   +0x14 u8  size_bits (32/64/128)
   +0x15 u8  (pad)
   +0x16 u8  dir ('W'=0x57 / 'R'=0x52)
   +0x17 u8  src
Records are chronological (oldest first). ring.txt: "# idx frame pc addr size dir src value_hi:value_lo"
"""
import os, sys, struct, json

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
DUMPS = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\hookdumps")
OUT = os.path.join(ROOT, r"work\builds\GR_USERDUMP\out")

MSTATE = 0x0055B7A0
BUCKET_BASE = 0x0055B7A8
BUCKETS = 128
BUCKET_END = BUCKET_BASE + BUCKETS * 8          # 0x0055BBA8
REGION = (MSTATE, BUCKET_END)                    # mstate + whole bucket array
B126_FD = 0x0055BB98
B126_BK = 0x0055BB9C

def parse_ring(path):
    b = open(path, "rb").read()
    n = len(b) // 24
    recs = []
    for i in range(n):
        o = i * 24
        fr, pc, ad = struct.unpack_from("<III", b, o)
        val = struct.unpack_from("<Q", b, o + 12)[0]
        size, pad, dr, src = b[o + 20], b[o + 21], b[o + 22], b[o + 23]
        recs.append((i, fr, pc, ad, size, chr(dr) if 32 <= dr < 127 else "?", src, val))
    return recs

def overlaps(ad, size, lo, hi):
    w = max(1, size // 8)
    return (ad < hi) and (ad + w > lo)

def main():
    os.makedirs(OUT, exist_ok=True)
    for tag, dn in (("OLD_f19701", "hook_19701_hotkey_f10"),
                    ("NEW_f23444", "hook_23444_hotkey_f10")):
        recs = parse_ring(os.path.join(DUMPS, dn, "ring.bin"))
        lines = []
        A = lines.append
        A("=" * 110)
        A("%s  (%s)   records=%d" % (tag, dn, len(recs)))
        A("  frame span of ring: %d .. %d" % (recs[0][1], recs[-1][1]))
        A("=" * 110)

        # sanity check vs ring.txt for first 3 and last 3
        p = os.path.join(OUT, "g2_%s_check.txt" % tag)
        with open(p, "w", encoding="utf-8") as f:
            for r in recs[:3] + recs[-3:]:
                f.write("%d %d %s %s %d %s %d %016X\n" % (r[0], r[1], "%08X" % r[2], "%08X" % r[3], r[4], r[5], r[6], r[7]))

        # 1) every store into the mstate+bucket region
        reg = [r for r in recs if overlaps(r[3], r[4], *REGION)]
        A("")
        A("[1] stores overlapping mstate+bucket region 0x%08X..0x%08X : %d records" % (REGION[0], REGION[1], len(reg)))

        # 2) stores touching the bucket-126 slots
        b126 = [r for r in recs if overlaps(r[3], r[4], B126_FD, B126_BK + 4)]
        A("")
        A("[2] stores overlapping BUCKET-126 slots 0x%08X/0x%08X : %d records" % (B126_FD, B126_BK, len(b126)))
        A("     idx  frame  pc        addr      size dir src  value")
        for (i, fr, pc, ad, size, dr, src, val) in b126:
            A("     %-6d %-6d %08X  %08X  %-4d %s   %d    0x%016X" % (i, fr, pc, ad, size, dr, src, val))

        # 3) any record anywhere carrying the known corrupt value
        for target, nm in ((0x6ED47823, "0x6ED47823"), (0xA73D37F0, "0xA73D37F0"), (0x6E6A338, "0x6E6A338")):
            hits = [r for r in recs if (r[7] & 0xFFFFFFFF) == target or (r[7] >> 32) == target]
            A("")
            A("[3] records whose value contains %s : %d" % (nm, len(hits)))
            for (i, fr, pc, ad, size, dr, src, val) in hits[:60]:
                A("     %-6d %-6d %08X  %08X  %-4d %s   %d    0x%016X" % (i, fr, pc, ad, size, dr, src, val))
            if len(hits) > 60:
                A("     ... (%d more)" % (len(hits) - 60))

        # 4) any record whose ADDRESS is one of the wild addresses
        for target, nm in ((0x6ED4782B, "0x6ED4782B"), (0x6ED47823, "0x6ED47823"), (0x6E6A340, "0x6E6A340"), (0x6E6A338, "0x6E6A338")):
            hits = [r for r in recs if r[3] == target]
            A("")
            A("[4] records whose addr == %s : %d" % (nm, len(hits)))
            for (i, fr, pc, ad, size, dr, src, val) in hits[:40]:
                A("     %-6d %-6d %08X  %08X  %-4d %s   %d    0x%016X" % (i, fr, pc, ad, size, dr, src, val))

        # 5) per-bucket write histogram in the region + top PCs
        from collections import Counter
        cpc = Counter()
        cbk = Counter()
        for (i, fr, pc, ad, size, dr, src, val) in reg:
            cpc["%08X" % pc] += 1
            if BUCKET_BASE <= ad < BUCKET_END:
                cbk[(ad - BUCKET_BASE) // 8] += 1
        A("")
        A("[5] top writer PCs inside the region (count):")
        for pc, c in cpc.most_common(30):
            A("     %s  x%d" % (pc, c))
        A("")
        A("[5b] buckets written (idx -> count), only buckets with writes:")
        A("     " + ", ".join("%d:%d" % (k, v) for k, v in sorted(cbk.items())))

        # 6) print the whole region record list
        A("")
        A("[6] full chronological list of region stores (%d):" % len(reg))
        A("     idx  frame  pc        addr      size dir src  value")
        for (i, fr, pc, ad, size, dr, src, val) in reg:
            A("     %-6d %-6d %08X  %08X  %-4d %s   %d    0x%016X" % (i, fr, pc, ad, size, dr, src, val))

        with open(os.path.join(OUT, "g2_%s.txt" % tag), "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("%s: records=%d span=%d..%d region=%d b126=%d" % (tag, len(recs), recs[0][1], recs[-1][1], len(reg), len(b126)))
        for r in b126:
            print("   b126 store: idx=%d frame=%d pc=%08X addr=%08X size=%d %s val=0x%016X" % (r[0], r[1], r[2], r[3], r[4], r[5], r[7]))

if __name__ == "__main__":
    main()
