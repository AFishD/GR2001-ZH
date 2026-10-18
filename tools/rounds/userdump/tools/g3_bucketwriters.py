# -*- coding: utf-8 -*-
"""G3: classify every ring store into the bucket array by (slot-kind, value-kind) per PC.

For a store at addr inside [0x55B7A8, 0x55BBA8):
    bucket = (addr - 0x55B7A8) // 8 ; field = 'fd' if (addr-0x55B7A8)%8==0 else 'bk'
value classification:
    SELF   value == pseudo(bucket) == 0x55B798 + 8*bucket   -> empty-bin restore / unlink-tail
    CHUNK  value < 0x02000000 and value % 8 == 0           -> a real heap chunk address (link/insert)
    MSTATE value in [0x55B7A0,0x55B7A8)                    -> mstate self pointers
    OTHER  anything else (incl. out-of-RAM pointers)
"""
import os, struct
from collections import defaultdict, Counter

ROOT = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
DUMPS = os.path.join(ROOT, r"work\builds\GR_HOOKEMU_QT2\qt\hookdumps")
OUT = os.path.join(ROOT, r"work\builds\GR_USERDUMP\out")
MSTATE = 0x0055B7A0
BB = 0x0055B7A8
BE = BB + 128 * 8

def pseudo(i):
    return 0x0055B798 + 8 * i

def parse_ring(path):
    b = open(path, "rb").read()
    out = []
    for i in range(len(b) // 24):
        o = i * 24
        fr, pc, ad = struct.unpack_from("<III", b, o)
        val = struct.unpack_from("<Q", b, o + 12)[0]
        size, pad, dr, src = b[o + 20], b[o + 21], b[o + 22], b[o + 23]
        out.append((i, fr, pc, ad, size, dr, src, val))
    return out

def classify(v):
    lo = v & 0xFFFFFFFF
    if v > 0xFFFFFFFF:
        return "OTHER64"
    if lo % 8 == 0 and 0x1000 <= lo < 0x02000000:
        return "CHUNK"
    if 0x55B798 <= lo < 0x55C000:
        return "SELF/MSTATE"
    if lo == 0:
        return "ZERO"
    return "OTHER"

def main():
    for tag, dn in (("OLD_f19701", "hook_19701_hotkey_f10"),
                    ("NEW_f23444", "hook_23444_hotkey_f10")):
        recs = parse_ring(os.path.join(DUMPS, dn, "ring.bin"))
        L = []
        A = L.append
        A("=" * 110)
        A("%s ring span frames %d..%d  records=%d" % (tag, recs[0][1], recs[-1][1], len(recs)))
        A("=" * 110)

        # per-PC per-(field,kind) counters
        tab = defaultdict(Counter)
        samples = defaultdict(list)
        bkidx = defaultdict(Counter)
        for (i, fr, pc, ad, size, dr, src, val) in recs:
            w = max(1, size // 8)
            # a store may cover 1..2 bucket slots
            for off in range(0, w, 4):
                a = ad + off
                if BB <= a < BE:
                    b = (a - BB) // 8
                    fld = "fd" if (a - BB) % 8 == 0 else "bk"
                    k = classify(val >> (8 * off) & 0xFFFFFFFFFFFFFFFF if size > 32 else val)
                    pcs = "%08X" % pc
                    tab[pcs][fld + ":" + k] += 1
                    v = (val >> (8 * off)) & 0xFFFFFFFF if size > 32 else (val & 0xFFFFFFFF)
                    if len(samples[pcs]) < 6:
                        samples[pcs].append((fr, a, b, fld, k, v))
                    bkidx[pcs][b] += 1

        A("")
        A("[A] PC -> (bucket-field : value-kind) counts   [only PCs that touch the bucket array]")
        rows = sorted(tab.items(), key=lambda kv: -sum(kv[1].values()))
        for pcs, c in rows:
            A("  PC=%s  total=%d" % (pcs, sum(c.values())))
            for k, n in c.most_common():
                A("       %-14s x%d" % (k, n))
            A("       buckets touched: %s" % ", ".join("%d:%d" % (b, n) for b, n in sorted(bkidx[pcs].items())))
            for (fr, a, b, fld, k, v) in samples[pcs]:
                A("       sample f=%-6d addr=0x%08X bucket=%-3d %s %-11s value=0x%08X" % (fr, a, b, fld, k, v))
            A("")

        # the decisive question: which PC ever writes a HIGH bucket (>=110, the large-bin range) with a CHUNK value
        A("")
        A("[B] PCs writing bucket idx >= 110 (large-bin range) at all:")
        seen = False
        for pcs, c in rows:
            hi = {b: n for b, n in bkidx[pcs].items() if b >= 110}
            if hi:
                seen = True
                A("  PC=%s  %s" % (pcs, ", ".join("%d:%d" % (b, n) for b, n in sorted(hi.items()))))
        if not seen:
            A("  (none)")

        # [C] exact records for bin 126 neighbours 125/127 and the highest bins
        A("")
        A("[C] every ring store to buckets 118..127 (the large-bin tail) in this window:")
        n = 0
        for (i, fr, pc, ad, size, dr, src, val) in recs:
            w = max(1, size // 8)
            for off in range(0, w, 4):
                a = ad + off
                if BB <= a < BE and (a - BB) // 8 >= 118:
                    n += 1
                    b = (a - BB) // 8
                    fld = "fd" if (a - BB) % 8 == 0 else "bk"
                    v = (val >> (8 * off)) & 0xFFFFFFFF
                    A("   idx=%d %s pc=%08X addr=%08X size=%d value=0x%08X  frame=%d" % (b, fld, pc, a, size, v, fr))
        A("   total=%d" % n)

        # [D] which PCs write a slot with a *pseudo/self* value for HIGH buckets
        A("")
        A("[D] PCs writing bucket idx >= 100 with a self-referential value (= empty-bin restore):")
        seen = False
        for (i, fr, pc, ad, size, dr, src, val) in recs:
            if BB <= ad < BE:
                b = (ad - BB) // 8
                if b >= 100 and size == 32 and (val & 0xFFFFFFFF) == pseudo(b):
                    A("   pc=%08X addr=%08X bucket=%d frame=%d value=0x%08X" % (pc, ad, b, fr, val & 0xFFFFFFFF))
                    seen = True
        if not seen:
            A("   (none)")

        open(os.path.join(OUT, "g3_%s.txt" % tag), "w", encoding="utf-8").write("\n".join(L))
        print("%s: %d PCs touch the bucket array; bucket-array writes=%d"
              % (tag, len(rows), sum(sum(c.values()) for _, c in rows)))

if __name__ == "__main__":
    main()
