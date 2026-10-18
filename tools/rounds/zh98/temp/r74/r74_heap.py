# r74_heap.py - READ-ONLY. Inspect the game heap in a savestate's eeMemory.bin:
#   * dump the dlmalloc arena (malloc_state) fields
#   * resolve chunk headers and bin lists
#   * search for the bogus pointer 0x022D161C / value 0x4154536F
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "iso_build"))
import fix_zh116_p2s as R  # noqa: E402

EE_SIZE = 0x02000000


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def u64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def s32(v):
    return v - 0x100000000 if v & 0x80000000 else v


def main():
    p2s = sys.argv[1]
    ee = R.read_entry(p2s, "eeMemory.bin")
    print("eeMemory.bin = %d bytes (0x%x)  -> max VA 0x%08X" % (len(ee), len(ee), len(ee) - 1))
    print("")

    probes = [int(x, 16) for x in sys.argv[2:]] or [0x022D161C, 0x022D1624, 0x022D162C]
    for a in probes:
        print("=== VA 0x%08X ===" % a)
        if a >= len(ee):
            print("   OUT OF MAPPED EE RAM (>= 0x%08X) -- not present in this savestate" % EE_SIZE)
        else:
            for off in range(0, 0x30, 8):
                print("   +0x%02x  u64=0x%016X  u32=0x%08X 0x%08X" % (
                    off, u64(ee, a + off), u32(ee, a + off), u32(ee, a + off + 4)))
        print("")

    # find candidate arenas: at arena+0x10 and arena+0x14 we expect fd/bk of smallbin[0]
    # pointing back to arena+0x10 (self-referential sentinel).
    print("=== scanning for dlmalloc arena candidates (fd==bk==arena+0x10 pattern) ===")
    hits = []
    for a in range(0, min(len(ee), EE_SIZE) - 0x40, 4):
        p = a + 0x10
        if u32(ee, p) == p and u32(ee, p + 4) == p:
            # check more bins are self-referential
            ok = 0
            for b in range(0, 128, 8):
                if u32(ee, p + b) == p + b:
                    ok += 1
            if ok >= 20:
                hits.append((a, ok))
    print("   candidates: %d" % len(hits))
    for a, ok in hits[:12]:
        print("     arena@0x%08X  self-ref bins=%d  top=0x%08X  flag=0x%08X" % (
            a, ok, u32(ee, a + 8), u32(ee, a + 4)))
    print("")

    # search for the bogus pointer value anywhere as u32
    print("=== search eeMemory for value 0x022D161C / 0x022D1624 / 0x022D162C (u32 LE) ===")
    for v in (0x022D161C, 0x022D1624, 0x022D162C, 0x4154536F):
        needle = struct.pack("<I", v)
        found = []
        s = 0
        while True:
            i = ee.find(needle, s)
            if i < 0:
                break
            found.append(i)
            s = i + 1
            if len(found) > 20:
                break
        print("   0x%08X -> %d hits %s" % (v, len(found),
              " ".join("0x%07x" % f for f in found[:12])))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
