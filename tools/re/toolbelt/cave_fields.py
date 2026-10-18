# -*- coding: utf-8 -*-
r"""cave_fields.py -- print the raw rs/rt/rd/sa/funct fields of a word list, so that
3-operand EE forms (MULT rd,rs,rt / MMI) can be told apart from the 2-operand MIPS forms.

usage: python cave_fields.py <elf> <loVA> <hiVA>
"""
import sys

sys.path.insert(0, __file__.rsplit("\\", 1)[0])
from cave_dis import Elf, GPR  # noqa: E402


def main():
    elf = Elf(sys.argv[1])
    lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
    for va in range(lo, hi, 4):
        w = elf.word(va)
        op = (w >> 26) & 0x3F
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        rd = (w >> 11) & 0x1F
        sa = (w >> 6) & 0x1F
        fn = w & 0x3F
        if op == 0 and fn in (0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x10, 0x12):
            print("  %08X  %08X  op=%02X rs=%2d(%-4s) rt=%2d(%-4s) rd=%2d(%-4s) sa=%2d fn=%02X"
                  % (va, w, op, rs, GPR[rs], rt, GPR[rt], rd, GPR[rd], sa, fn))
        elif op == 0x1C:
            print("  %08X  %08X  op=%02X(MMI grp=%d) rs=%2d(%-4s) rt=%2d(%-4s) rd=%2d(%-4s) sa=%2d fn=%02X"
                  % (va, w, op, w & 7, rs, GPR[rs], rt, GPR[rt], rd, GPR[rd], sa, fn))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
