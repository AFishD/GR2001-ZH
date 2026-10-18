# -*- coding: utf-8 -*-
r"""r69_syms.py — 在 ELF 符号表里按关键字查符号 (只读)。

用法: python r69_syms.py <elf> <关键字> [关键字...]
"""
import os
import struct
import sys

SEC_ADDR = 0x00100000
STRTAB_OFF, STRTAB_LEN = 0x4DEDE0, 0x13E199
SYMTAB_OFF, SYMTAB_LEN = 0x61CF80, 0x97420


def main():
    elf = sys.argv[1]
    keys = [k.lower() for k in sys.argv[2:]]
    data = open(elf, 'rb').read()
    strtab = data[STRTAB_OFF:STRTAB_OFF + STRTAB_LEN]
    out = []
    p, end = SYMTAB_OFF, SYMTAB_OFF + SYMTAB_LEN
    while p + 16 <= end:
        name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p)
        p += 16
        if not name:
            continue
        n = strtab[name:strtab.index(b'\0', name)].decode('latin-1')
        if any(k in n.lower() for k in keys):
            out.append((value, size, n, info, shndx))
    out.sort()
    print('共 %d 个匹配符号' % len(out))
    for value, size, n, info, shndx in out:
        print('  %08X  size=%-6d shndx=%-3d %s' % (value, size, shndx, n))
        if value == 0:
            continue
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
