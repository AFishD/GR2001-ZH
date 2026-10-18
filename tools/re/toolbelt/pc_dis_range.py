#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_dis_range.py -- 任意 VA 区间对齐反汇编 (round77)"""
import os
import sys

import capstone
import pefile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXE = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "GhostRecon.exe")


def main():
    va0 = int(sys.argv[1], 16)
    va1 = int(sys.argv[2], 16)
    pe = pefile.PE(EXE, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    blob = open(EXE, "rb").read()
    for s in pe.sections:
        sva = base + s.VirtualAddress
        if sva <= va0 < sva + s.SizeOfRawData:
            off = s.PointerToRawData + (va0 - sva)
            code = blob[off:off + (va1 - va0)]
            md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
            for ins in md.disasm(code, va0):
                print("%08x  %-22s %s %s" %
                      (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
            return
    print("VA 不在任何节内")


if __name__ == "__main__":
    main()
