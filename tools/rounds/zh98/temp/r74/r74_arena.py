# r74_arena.py - READ-ONLY. Locate the dlmalloc arena and the corrupted chunks in the
# reproduced crash-scene EE RAM dump, so the 0x22D161C / 0x14 pointers can be placed.
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
RAM = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r74",
                   "dump_r74_r1only", "reclut_f00000305_eeram.bin")


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def main():
    ee = open(RAM, "rb").read()
    print("dump = %s" % os.path.basename(RAM))
    print("size = %d (0x%X)" % (len(ee), len(ee)))
    print("")

    # A dlmalloc arena's smallbin[i] sentinel is a chunk whose fd/bk point at itself.
    # At arena+0x10 we therefore expect u32(arena+0x10)==arena+0x10 and same for +0x14.
    print("=== arena candidates (many self-referential bins) ===")
    cands = []
    for a in range(0x00100000, 0x02000000 - 0x200, 8):
        p = a + 0x10
        if u32(ee, p) != p or u32(ee, p + 4) != p:
            continue
        ok = 0
        for b in range(0, 0x100, 8):
            if u32(ee, p + b) == p + b:
                ok += 1
        if ok >= 24:
            cands.append((a, ok))
    for a, ok in cands[:10]:
        print("   arena@0x%08X  selfref_bins=%d  top(arena+8)=0x%08X  flag(arena+4)=0x%08X"
              % (a, ok, u32(ee, a + 8), u32(ee, a + 4)))
    print("   total candidates: %d" % len(cands))
    print("")

    print("=== small pointer values seen in the user's log, searched in RAM ===")
    for v in (0x14, 0x10, 0x22D161C, 0x22D1624, 0x22D162C, 0x4154536F):
        n = struct.pack("<I", v)
        hits = []
        s = 0
        while True:
            i = ee.find(n, s)
            if i < 0:
                break
            hits.append(i)
            s = i + 1
            if len(hits) > 400:
                break
        print("   0x%08X -> %4d u32 occurrences%s" % (
            v, len(hits), "" if not hits else "  first: " + " ".join("0x%07x" % h for h in hits[:8])))
    print("")

    print("=== heap-top pointer sanity: value at arena+8 should be a valid RAM address ===")
    for a, ok in cands[:6]:
        top = u32(ee, a + 8)
        print("   arena@0x%08X top=0x%08X %s" % (
            a, top, "OK (in RAM)" if 0x100000 <= top < 0x02000000 else "!! OUT OF RAM"))
    print("")

    print("=== stack region (sp=0x01FFE610) ===")
    for o in range(0x01FFE5C0, 0x01FFE680, 16):
        print("   %08x  %s |%s|" % (
            o, " ".join("%02x" % c for c in ee[o:o + 16]),
            "".join(chr(c) if 32 <= c < 127 else "." for c in ee[o:o + 16])))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
