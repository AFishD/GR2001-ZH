# -*- coding: utf-8 -*-
r"""cave_probe.py -- three targeted checks for the round79 cave audit.

 1) spill   -- in the function containing 0x21CD70, is the stack slot sp+252 ever written?
               (the j-patch at 0x21CD70 rewrote its delay slot to `lw a0,252(sp)`)
 2) ptr     -- are the dead-looking original functions inside cave block A referenced by a
               *literal 32-bit pointer* anywhere in the ELF (vtable / function table)?
 3) len     -- around the j-patch at 0x3070B4, how did the ORIGINAL obtain the string
               length that the cave now reads with `lhu a1,2(t0)`?

usage: python cave_probe.py spill|ptr|len
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cave_dis import Elf, dis  # noqa: E402

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ORIG = os.path.join(REPO, r"third_party\orig\ps2\slus_out\SLUS_206.13")
CUR = os.path.join(REPO, r"work\builds\GR_ZH98\temp\r79\dump\elf_zh113b.bin")


def func_start(elf, va, back=0x1000):
    """nearest addiu sp,sp,-N prologue at or below va"""
    for v in range(va, va - back, -4):
        w = elf.word(v)
        if (w >> 26) & 0x3F == 9 and ((w >> 21) & 0x1F) == 29 and ((w >> 16) & 0x1F) == 29:
            imm = w & 0xFFFF
            if imm & 0x8000:
                return v
    return None


def spill():
    do, dc = Elf(ORIG), Elf(CUR)
    for tag, elf in (("ORIG", do), ("CUR", dc)):
        s = func_start(elf, 0x21CD70)
        e = s + 0x600
        print("\n=== %s function containing 0x21CD70: prologue 0x%08X (scan to 0x%08X) ==="
              % (tag, s, e))
        hits = 0
        for va in range(s, e, 4):
            w = elf.word(va)
            op = (w >> 26) & 0x3F
            if op in (0x28, 0x29, 0x2B, 0x3F):     # sb sh sw sd
                simm = w & 0xFFFF
                simm = simm - 0x10000 if simm & 0x8000 else simm
                rs = (w >> 21) & 0x1F
                if rs == 29 and 0xF0 <= simm <= 0x108:
                    print("   %08X  %s" % (va, dis(w, va)))
                    hits += 1
        if not hits:
            print("   (no stores into sp+0xF0..0x108)")
        # also dump the code path into the patched site
        print("   -- code 0x21CD50..0x21CD90 --")
        for va in range(0x21CD50, 0x21CD90, 4):
            a, b = do.word(va), dc.word(va)
            print("   %08X  orig=%-40s cur=%-40s%s"
                  % (va, dis(a, va), dis(b, va), "  <<" if a != b else ""))


DEAD = [0x416ED0, 0x416EF0, 0x4170A0, 0x4170C0, 0x416EC8, 0x417098, 0x4170B8,
        0x417328, 0x417330, 0x41744C, 0x417450, 0x417468, 0x417470,
        0x417534, 0x417538, 0x41769C, 0x4176A0, 0x4177F4, 0x4177F8]


def ptr():
    dc = Elf(CUR)
    print("=== literal 32-bit pointers to cave-block-A function entries? ===")
    for tgt in DEAD:
        needle = struct.pack("<I", tgt)
        hits = []
        i = dc.d.find(needle)
        while i >= 0:
            hits.append(i)
            i = dc.d.find(needle, i + 1)
        # map file offsets back to VAs where possible
        vas = []
        for h in hits:
            for (v, o, fs) in dc.segs:
                if o <= h < o + fs:
                    vas.append(v + (h - o))
        print("   0x%08X  %d occurrence(s)  file_off=%s  VA=%s"
              % (tgt, len(hits), [hex(h) for h in hits[:6]],
                 ["0x%08X" % x for x in vas[:6]]))


def lensite():
    do, dc = Elf(ORIG), Elf(CUR)
    print("=== 0x307060..0x307100  (j-patch 0x3070B4 -> 0x5657C8) ===")
    for va in range(0x307060, 0x307100, 4):
        a, b = do.word(va), dc.word(va)
        print("   %08X  orig=%-40s cur=%-40s%s"
              % (va, dis(a, va), dis(b, va), "  <<" if a != b else ""))
    print("\n=== 0x21CA00..0x21CA60 (j-patch 0x21CA50 -> 0x565730) ===")
    for va in range(0x21CA00, 0x21CA60, 4):
        a, b = do.word(va), dc.word(va)
        print("   %08X  orig=%-40s cur=%-40s%s"
              % (va, dis(a, va), dis(b, va), "  <<" if a != b else ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    m = sys.argv[1]
    {"spill": spill, "ptr": ptr, "len": lensite}[m]()
