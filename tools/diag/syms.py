# -*- coding: utf-8 -*-
r"""syms.py — ELF 符号表检索
用法: python syms.py <正则> [--size] [--elf <ELF路径>]
默认 ELF = work/builds/GR_ZH72/temp/SLUS_206.13.zh72 (换盘时用 --elf 指新盘 temp 下的 ELF)
"""
import bisect
import os
import re
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH72', 'temp', 'SLUS_206.13.zh72')
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00


def load(path):
    data = open(path, 'rb').read()
    strtab = data[0x4DEDE0:0x4DEDE0 + 0x13E199]
    syms = []
    p, end = 0x61CF80, 0x61CF80 + 0x97420
    while p < end:
        name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p)
        p += 16
        if name:
            n = strtab[name:strtab.index(b'\0', name)].decode('latin-1')
            syms.append((value, size, info, n))
    return data, syms


def main():
    args = sys.argv[1:]
    pat = args[0]
    show_size = '--size' in args
    elf = args[args.index('--elf') + 1] if '--elf' in args else ELF
    data, syms = load(elf)
    rx = re.compile(pat, re.I)
    hits = sorted([s for s in syms if rx.search(s[3])])
    for value, size, info, n in hits:
        if show_size:
            print('%08X %6d %s' % (value, size, n))
        else:
            print('%08X %s' % (value, n))
    print('# %d / %d 符号' % (len(hits), len(syms)), file=sys.stderr)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
