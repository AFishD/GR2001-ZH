# -*- coding: utf-8 -*-
r"""m17_disasm.py — 反汇编 cctc cave (0x417050..0x417150, UV 计算) 与相关 cave, 读出引擎的
pair / 单字节 两条 UV 公式的确切实现 (含 +1 / +576 之类的偏置来源)。
只读。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
import capstone                                        # noqa: E402

md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
md.detail = False

data = open(ISO, 'rb').read(8 << 20)


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def dis(va0, va1, title):
    o = elf_off(va0)
    code = data[o:o + (va1 - va0)]
    print('=' * 78)
    print('%s   VA 0x%X..0x%X  (%d B, file 0x%X)' % (title, va0, va1, len(code), o))
    print('=' * 78)
    for ins in md.disasm(code, va0):
        print('  0x%06X  %-10s %s' % (ins.address, ins.mnemonic, ins.op_str))
    print()


dis(0x416ED0, 0x416F40, 'ds16 cave (字节→16位合成)')
dis(0x416F40, 0x417050, 'cw cave (CharWidth, pair-aware)')
dis(0x417050, 0x417150, 'cctc cave (UV 计算)')
