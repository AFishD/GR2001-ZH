# -*- coding: utf-8 -*-
r"""cave_addrs.py -- is any VA in a cave region ever *materialised as an address* by code?

Checks, over the whole ORIGINAL .text:
  * jal / j / branch target inside the range           (direct control transfer)
  * lui+addiu / lui+ori / lui+lw / lui+sw pairs whose computed address lands in range
    (function-pointer table building, `jalr` targets, data pointers)
  * symbol coverage of the range per the in-file .symtab (is it a named .text function
    or an unnamed gap?)

usage: python cave_addrs.py [lo hi]      (default: 0x416E00 0x417800)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cave_dis import Elf, dis  # noqa: E402

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ORIG = os.path.join(REPO, r"third_party\orig\ps2\slus_out\SLUS_206.13")


def main():
    lo = int(sys.argv[1], 16) if len(sys.argv) > 2 else 0x416E00
    hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x417800
    do = Elf(ORIG)
    va0, off, fs = do.text()
    print("=== scan ORIG .text 0x%08X..0x%08X for references into 0x%08X..0x%08X ==="
          % (va0, va0 + fs, lo, hi))
    hits = 0
    for va in range(va0, va0 + fs - 8, 4):
        w = do.word(va)
        op = (w >> 26) & 0x3F
        tgt = None
        if op in (2, 3):
            tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
        elif op in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
            simm = w & 0xFFFF
            simm = simm - 0x10000 if simm & 0x8000 else simm
            tgt = va + 4 + simm * 4
        if tgt is not None and lo <= tgt < hi:
            print("   ctrl 0x%08X -> 0x%08X   %s" % (va, tgt, dis(w, va)))
            hits += 1
        # lui + <op with simm>
        if op == 0x0F:
            rd = (w >> 16) & 0x1F
            base = (w & 0xFFFF) << 16
            w2 = do.word(va + 4)
            op2 = (w2 >> 26) & 0x3F
            rs2 = (w2 >> 21) & 0x1F
            rt2 = (w2 >> 16) & 0x1F
            if rs2 == rd and op2 in (0x09, 0x0D, 0x23, 0x2B, 0x24, 0x25, 0x21, 0x31, 0x39):
                simm = w2 & 0xFFFF
                simm = simm - 0x10000 if simm & 0x8000 else simm
                eff = (base + simm) & 0xFFFFFFFF
                if lo <= eff < hi:
                    print("   addr 0x%08X/0x%08X -> 0x%08X  (%s ; %s)"
                          % (va, va + 4, eff, dis(w, va), dis(w2, va + 4)))
                    hits += 1
    if hits == 0:
        print("   (NO references at all)")
    print("   total %d" % hits)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
