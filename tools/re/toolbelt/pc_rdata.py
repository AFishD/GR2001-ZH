#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rdata.py -- 读 GhostRecon.exe 指定 VA 的字面量 (round77)"""
import os
import sys

import pefile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXE = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "GhostRecon.exe")


def main():
    pe = pefile.PE(EXE, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    blob = open(EXE, "rb").read()
    for a in sys.argv[1:]:
        va = int(a, 16)
        for s in pe.sections:
            sva = base + s.VirtualAddress
            if sva <= va < sva + s.SizeOfRawData:
                off = s.PointerToRawData + (va - sva)
                raw = blob[off:off + 64]
                end = raw.find(b"\x00")
                print("VA 0x%08x  file=0x%07x  bytes=%s  str=%r" %
                      (va, off, raw[:24].hex(), raw[:end if end >= 0 else 64]))
                break
        else:
            print("VA 0x%08x  not in any section" % va)


if __name__ == "__main__":
    main()
