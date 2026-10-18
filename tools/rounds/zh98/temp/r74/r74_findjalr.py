# r74_findjalr.py - READ-ONLY. Find the code site that transferred control to a low
# address, using the reproduced crash-scene eeMemory dump + the ELF symbol table.
#
# At the crash we have ra = 0x8, so some `jalr` set ra = 8 (or we fell out of a
# function whose caller's return address was 8).  The worker sets ra: `jalr t9` at
# ...f810.  So the cube ran `jalr $25` with $25 == the *address* 0x08.
#
# The cube's pointer bytes are controlled by the caller, so we must find the
# `jalr $25` site that pushed 0x8 into $25.  Candidates:
#   A) `sw X, 8($s0)`  (op=0x2B, rt=0x10, imm=8)  -> interp table entry = 8
#   B) `addiu $t9, $s0, 8` (op=0x09, rs=0x10, rt=0x19, imm=8)
#   C) `addiu $v0/$a0/$a1, $s0, 8`
#   D) `lw $25, 8($s0)` (op=0x23, rt=0x19, imm=8)
#   E) `sw $t9, 8($s0)` etc.
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
sys.path.insert(0, os.path.join(REPO, "tools", "rounds", "zh98", "temp", "r74"))
import r74_mips as M  # noqa: E402

D = os.path.join(REPO, "work", "builds", "GR_ZH98", "temp", "r74", "dump_r74_zh111_cycle")
EE = os.path.join(D, "reclut_f00000785_eeram.bin")
RAM_LO, RAM_HI = 0x00100000, 0x00200000 + 0x1000000  # scan whole 32MB but report VA

S0 = 0x10


def main():
    ram = open(EE, "rb").read()
    print("eeMemory = %d B" % len(ram))

    patterns = [
        ("A sw ?,8($s0)",       0x2B, None, S0, 8),
        ("B addiu $t9,$s0,8",   0x09, S0, 0x19, 8),
        ("C addiu $a0,$s0,8",   0x09, S0, 0x04, 8),
        ("C2 addiu $v0,$s0,8",  0x09, S0, 0x02, 8),
        ("C3 addiu $a1,$s0,8",  0x09, S0, 0x05, 8),
        ("D lw $25,8($s0)",     0x23, S0, 0x19, 8),
        ("E sw $t9,8($s0)",     0x2B, S0, 0x19, 8),
        ("F sw $v0,8($s0)",     0x2B, S0, 0x02, 8),
        ("G addiu $t9,$sp,8",   0x09, 29, 0x19, 8),
    ]

    enc = []
    for nm, op, rs, rt, imm in patterns:
        w = (op << 26) | (((rs if rs is not None else 0)) << 21) | (rt << 16) | (imm & 0xFFFF)
        if rs is None:
            # rt is the only constraint
            mask = (0x3F << 26) | (0x1F << 16) | 0xFFFF
            val = (op << 26) | (rt << 16) | (imm & 0xFFFF)
        else:
            mask = (0x3F << 26) | (0x1F << 21) | (0x1F << 16) | 0xFFFF
            val = w
        enc.append((nm, mask, val))

    hits = {nm: [] for nm, _, _ in enc}
    for va in range(0x00100000, min(len(ram), 0x00600000) - 4, 4):
        w = struct.unpack_from("<I", ram, va)[0]
        for nm, mask, val in enc:
            if (w & mask) == val:
                hits[nm].append(va)

    for nm in hits:
        hs = hits[nm]
        print("")
        print("=== %-22s %d hits ===" % (nm, len(hs)))
        for va in hs[:40]:
            print("   0x%08X  %s" % (va, M.dis(struct.unpack_from("<I", ram, va)[0], va)))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
