# -*- coding: utf-8 -*-
r"""p10_syms.py — round42: 列出符号表里某个地址区间的函数名 (只读)"""
import bisect
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = os.path.join(REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13')
data = open(ELF, 'rb').read()
strtab = data[0x4DEDE0:0x4DEDE0 + 0x13E199]
syms = {}
p, end = 0x61CF80, 0x61CF80 + 0x97420
while p < end and p + 16 <= len(data):
    name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p)
    p += 16
    if name and value:
        try:
            n = strtab[name:strtab.index(b'\0', name)].decode('latin-1')
        except Exception:                                        # noqa: BLE001
            continue
        syms.setdefault(value, (n, size))
lo = int(sys.argv[1], 16) if len(sys.argv) > 1 else 0x219000
hi = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x21D000
for va in sorted(syms):
    if lo <= va < hi:
        n, size = syms[va]
        print('  %08X  %-4s  %s' % (va, size or '', n))
