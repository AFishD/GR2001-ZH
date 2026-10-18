# -*- coding: utf-8 -*-
r"""cave_syms.py -- read the ELF .symtab/.strtab that ships inside SLUS_206.13 and
resolve the VAs the round79 audit cares about.

The PS2 executable is a fully linked ELF with sh_type=2 (SYMTAB) + sh_type=3 (STRTAB)
kept in the file (they are past the single PT_LOAD, so they are not loaded at runtime,
but they are authoritative for *what the original code was*).

usage: python cave_syms.py [<addr> ...]        (defaults to the audit address list)
"""
import os
import struct
import sys

REPO = r"C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization"
ORIG = os.path.join(REPO, r"third_party\orig\ps2\slus_out\SLUS_206.13")
CUR = os.path.join(REPO, r"work\builds\GR_ZH98\temp\r79\dump\elf_zh113b.bin")

WATCH = [
    0x219A70, 0x219BCC, 0x219EB0, 0x219F50, 0x21AC00, 0x21AC74, 0x21AC90,
    0x21ACD0, 0x21AD10, 0x21ADE0, 0x21AE20, 0x21BD68, 0x21C048, 0x21C624,
    0x21CA50, 0x21CB28, 0x21CB3C, 0x21CC08, 0x21CD70, 0x21CFD8, 0x21D940,
    0x2ECEC0, 0x3070B4, 0x40BFC8, 0x407078, 0x408928, 0x411690,
    0x416ED0, 0x416EF0, 0x416F40, 0x417050, 0x4170A0, 0x4170C0, 0x417150,
    0x417200, 0x417330, 0x417450, 0x417470, 0x417500, 0x417538, 0x417650,
    0x417680, 0x4176A0, 0x4176B0, 0x4177F8, 0x565670, 0x565730, 0x565760,
    0x5657C8, 0x56583C, 0x565900, 0x565A00, 0x541CA0, 0x540F30, 0x541E90,
    0x53E2B0, 0x53E9E0, 0x53EAE0, 0x53EBE0, 0x53FD50, 0x540F60, 0x5414B0,
    0x118EE0, 0x519AC0, 0x518DE0, 0x5172E0,
]


def load_syms(path):
    d = open(path, "rb").read()
    e_shoff, = struct.unpack_from("<I", d, 0x20)
    e_shentsize, e_shnum = struct.unpack_from("<HH", d, 0x2E)
    shs = []
    for i in range(e_shnum):
        o = e_shoff + i * e_shentsize
        shs.append(struct.unpack_from("<10I", d, o))
    symtab = strtab = None
    for sh in shs:
        if sh[1] == 2:
            symtab = sh
        if sh[1] == 3 and strtab is None:
            strtab = sh
    assert symtab and strtab, (symtab, strtab)
    so, ss, slink = symtab[4], symtab[5], symtab[6]
    strsh = shs[slink] if slink < len(shs) else strtab
    sto, ssz = strsh[4], strsh[5]
    def sname(off):
        e = d.index(b"\0", sto + off)
        return d[sto + off:e].decode("latin-1")
    out = []
    for i in range(ss // 16):
        o = so + i * 16
        nm, val, size, info, other, shndx = struct.unpack_from("<IIIBBH", d, o)
        out.append((val, size, info, shndx, sname(nm)))
    return out


def main():
    want = [int(a, 16) for a in sys.argv[1:]] or WATCH
    for tag, path in (("ORIG(EN retail)", ORIG), ("CUR(GR_ZH113b)", CUR)):
        syms = load_syms(path)
        byva = {}
        for (val, size, info, shndx, nm) in syms:
            if val:
                byva.setdefault(val, (size, info, shndx, nm))
        print("\n===== %s : %d symbols =====" % (tag, len(syms)))
        for a in want:
            hit = byva.get(a)
            if hit:
                size, info, shndx, nm = hit
                kind = {0: "NOTYPE", 1: "OBJECT", 2: "FUNC", 3: "SECTION"}.get(info & 0xF, "?")
                print("   0x%08X  %-9s size=%-6d shndx=%-3d  %s" % (a, kind, size, shndx, nm))
            else:
                print("   0x%08X  (no symbol at this exact VA)" % a)
        # names for cave-block-A function entries (nearest symbol <= va)
        cand = sorted(v for v in byva if 0x416E00 <= v < 0x417800)
        print("   -- all symbols inside cave block A 0x416E00..0x417800 --")
        for v in cand:
            size, info, shndx, nm = byva[v]
            print("      0x%08X size=%-6d %s" % (v, size, nm))
        cand = sorted(v for v in byva if 0x565600 <= v < 0x565B00)
        print("   -- all symbols inside cave block B 0x565600..0x565B00 --")
        for v in cand:
            size, info, shndx, nm = byva[v]
            print("      0x%08X size=%-6d %s" % (v, size, nm))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
