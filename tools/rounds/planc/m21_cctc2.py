# -*- coding: utf-8 -*-
r"""m21_cctc2.py — 反汇编原始 ComputeCharTextureCoords (0x21ADE0 起) 看单字节路径如何取 UV。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
import capstone                                        # noqa: E402

md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
data = open(ISO, 'rb').read(8 << 20)


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def dis(va0, va1, title):
    print('=' * 70)
    print('%s  VA 0x%X..0x%X' % (title, va0, va1))
    print('=' * 70)
    o = elf_off(va0)
    for va in range(va0, va1, 4):
        w = data[o + (va - va0):o + (va - va0) + 4]
        txt = None
        for ins in md.disasm(w, va):
            txt = '%-10s %s' % (ins.mnemonic, ins.op_str)
        print('  0x%06X  %s  %s' % (va, w.hex(), txt if txt else '???? (坏字/数据)'))
    print()


dis(0x21ADC0, 0x21AE80, 'ComputeCharTextureCoords (hook @0x21ADE0 j 0x417050)')
