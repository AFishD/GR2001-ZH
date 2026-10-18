"""r73_probe_bytes.py -- compare ORIGINAL vs current ELF bytes around the font cave.

Read-only. Writes nothing except stdout.

Why: my Ghidra-driven raw decode of the "grid formula cave" (VA 0x417078..) produced a
few words that decode to nonsense (0x00007071 at 0x4170F4 where `mflo t6` is expected).
This script settles whether that is (a) genuine original code, (b) a localization patch
artifact, or (c) a wrong VA<->file-offset mapping on my side.
"""
import struct
import sys
import os

ORIG = r"third_party\orig\ps2\slus_out\SLUS_206.13"
CUR = r"work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf"


def load_phdrs(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:4] != b"\x7fELF":
        raise SystemExit("not ELF: " + path)
    e_phoff = struct.unpack_from("<I", data, 0x1C)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x2A)[0]
    e_phnum = struct.unpack_from("<H", data, 0x2C)[0]
    phdrs = []
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
            struct.unpack_from("<8I", data, off)
        phdrs.append(dict(type=p_type, off=p_offset, vaddr=p_vaddr,
                          filesz=p_filesz, memsz=p_memsz, flags=p_flags))
    return data, phdrs


def va_to_off(phdrs, va):
    for p in phdrs:
        if p["type"] == 1 and p["vaddr"] <= va < p["vaddr"] + p["memsz"]:
            return p["off"] + (va - p["vaddr"]), p
    return None, None


def dump(path, label, ranges):
    data, phdrs = load_phdrs(path)
    print("=" * 74)
    print(f"{label}: {path}  size={len(data)}")
    print("  PT_LOAD segments:")
    for p in phdrs:
        if p["type"] == 1:
            print(f"    vaddr=0x{p['vaddr']:08X} off=0x{p['off']:08X} "
                  f"filesz=0x{p['filesz']:08X} memsz=0x{p['memsz']:08X} flags=0x{p['flags']:X}")
    for (lo, hi, note) in ranges:
        print(f"  --- VA 0x{lo:08X}..0x{hi:08X}  {note}")
        for va in range(lo, hi, 4):
            off, p = va_to_off(phdrs, va)
            if off is None or off + 4 > len(data):
                print(f"    0x{va:08X}  <not mapped>")
                continue
            w = struct.unpack_from("<I", data, off)[0]
            print(f"    0x{va:08X}  {w:08X}")


RANGES = [
    (0x416FC0, 0x417010, "cave head / record-vs-grid branch"),
    (0x417040, 0x417140, "grid formula cave (62/16/2/12/3)"),
    (0x417140, 0x4171D0, "gate2 + StringWidth tail"),
    (0x21ADE0, 0x21AEC0, "RSFont::ComputeCharTextureCoords"),
    (0x21AC00, 0x21AC40, "RSFont::StringWidth"),
    (0x21AD10, 0x21AD60, "RSFont::CharWidth"),
]


def main():
    dump(ORIG, "ORIGINAL", RANGES)
    if os.path.exists(CUR):
        dump(CUR, "CURRENT(r72)", RANGES)
        d1, p1 = load_phdrs(ORIG)
        d2, p2 = load_phdrs(CUR)
        print("=" * 74)
        print("DIFF (original -> current) over the same ranges")
        for (lo, hi, note) in RANGES:
            for va in range(lo, hi, 4):
                o1, _ = va_to_off(p1, va)
                o2, _ = va_to_off(p2, va)
                if o1 is None or o2 is None:
                    continue
                w1 = struct.unpack_from("<I", d1, o1)[0]
                w2 = struct.unpack_from("<I", d2, o2)[0]
                if w1 != w2:
                    print(f"  0x{va:08X}  {w1:08X} -> {w2:08X}   {note}")
    else:
        print("(current ELF not found: " + CUR + ")")


main()
