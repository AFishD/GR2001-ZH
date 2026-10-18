# -*- coding: utf-8 -*-
r"""cave_refs.py -- which ORIGINAL functions live inside the cave regions we overwrote?

For every cave range, walk the ORIGINAL ELF:
  * list every function prologue (addiu sp,sp,-N ; sd ra...) that starts inside/near it
  * list every jal/j/branch in the whole .text whose target lands inside it
That tells us whether the "code cave" really was dead padding or a live function body.

usage: python cave_refs.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cave_dis import Elf, dis  # noqa: E402

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ORIG = os.path.join(REPO, r"third_party\orig\ps2\slus_out\SLUS_206.13")
CUR = os.path.join(REPO, r"work\builds\GR_ZH98\temp\r79\dump\elf_zh113b.bin")

REGIONS = [
    (0x411600, 0x411700, "cave B  (0x411690)"),
    (0x416E00, 0x417800, "cave block A  (0x416ED0..0x4176E8)"),
    (0x565600, 0x565B00, "cave block B  (0x565670..0x565A48)"),
    (0x407000, 0x407100, "cave N1 (0x407078)"),
    (0x408900, 0x408A00, "cave N2 (0x408928)"),
]


def main():
    do = Elf(ORIG)
    va0, off, fs = do.text()
    out = []
    for (lo, hi, label) in REGIONS:
        out.append("\n########## %s   0x%08X..0x%08X ##########" % (label, lo, hi))
        # 1. prologues inside the region
        out.append("-- function prologues inside region --")
        for va in range(lo, hi, 4):
            w = do.word(va)
            op = (w >> 26) & 0x3F
            rs = (w >> 21) & 0x1F
            rt = (w >> 16) & 0x1F
            if op == 9 and rs == 29 and rt == 29:
                nxt = do.word(va + 4)
                out.append("   prologue 0x%08X  %-30s | next %s"
                           % (va, dis(w, va), dis(nxt, va + 4)))
        # 2. any reference into the region from anywhere in .text
        out.append("-- references INTO region (jal / j / branch) --")
        nref = 0
        for va in range(va0, va0 + fs - 4, 4):
            w = do.word(va)
            op = (w >> 26) & 0x3F
            tgt = None
            if op in (2, 3):
                tgt = ((w & 0x03FFFFFF) << 2) | (va & 0xF0000000)
            elif op in (1, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
                simm = w & 0xFFFF
                simm = simm - 0x10000 if simm & 0x8000 else simm
                tgt = va + 4 + simm * 4
            elif op == 0x11 and ((w >> 21) & 0x1F) == 8:
                simm = w & 0xFFFF
                simm = simm - 0x10000 if simm & 0x8000 else simm
                tgt = va + 4 + simm * 4
            if tgt is not None and lo <= tgt < hi:
                kind = "jal" if op == 3 else ("j" if op == 2 else "branch")
                out.append("   %-6s from 0x%08X -> 0x%08X   %s"
                           % (kind, va, tgt, dis(w, va)))
                nref += 1
        if nref == 0:
            out.append("   (none)")
    txt = "\n".join(out)
    print(txt)
    fn = os.path.join(REPO, r"work\builds\GR_ZH98\temp\r79\dump\cave_refs.txt")
    open(fn, "w", encoding="utf-8").write(txt)
    print("\n-> %s" % fn)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
