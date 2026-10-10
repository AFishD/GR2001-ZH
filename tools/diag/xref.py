# -*- coding: utf-8 -*-
r"""xref.py — ELF 调用点扫描
用法: python xref.py <hexVA> [<hexVA> ...] [--elf <ELF路径>]   # 列出 jal/j 到该地址的所有站点
默认 ELF = work/builds/GR_ZH72/temp/SLUS_206.13.zh72
"""
import bisect
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH72', 'temp', 'SLUS_206.13.zh72')
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00


def fname(syms, keys, va):
    i = bisect.bisect_right(keys, va) - 1
    if i >= 0:
        k = keys[i]
        if 0 <= va - k < 0x8000:
            return '%s+0x%X' % (syms[k], va - k)
    return 'sub_%08X' % va


def main():
    args = sys.argv[1:]
    elf = args[args.index('--elf') + 1] if '--elf' in args else ELF
    targets = [x for x in args if not x.startswith('--') and x != elf]
    data = open(elf, 'rb').read()
    main_seg = data[SEC_OFF:SEC_OFF + SEC_SIZE]
    strtab = data[0x4DEDE0:0x4DEDE0 + 0x13E199]
    syms = {}
    p, end = 0x61CF80, 0x61CF80 + 0x97420
    while p < end:
        name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p)
        p += 16
        if name and value and SEC_ADDR <= value < SEC_ADDR + SEC_SIZE:
            n = strtab[name:strtab.index(b'\0', name)].decode('latin-1')
            syms.setdefault(value, n)
    keys = sorted(syms)
    for arg in targets:
        tgt = int(arg, 16)
        print('== xref to %08X (%s)' % (tgt, syms.get(tgt, '?')))
        n = 0
        for off in range(0, SEC_SIZE, 4):
            w = struct.unpack_from('<I', main_seg, off)[0]
            op = w >> 26
            if op in (2, 3) and ((w & 0x3FFFFFF) << 2) == tgt:
                va = SEC_ADDR + off
                print('   %08X  %s  (%s)' % (va, 'jal' if op == 3 else 'j  ', fname(syms, keys, va)))
                n += 1
        print('   # %d 处' % n)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
