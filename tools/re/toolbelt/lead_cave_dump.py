# -*- coding: utf-8 -*-
r"""lead_cave_dump.py — Lead 独立核对: 反汇编 cave 网格公式区 (VA 0x4170C0..0x417120)
只读 ISO; VA -> ISO = VA - 0x6C780
用法: python lead_cave_dump.py <iso> [va0] [va1]
"""
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
iso = sys.argv[1]
va0 = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x4170C0
va1 = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x417124
BIAS = 0x6C780

REG = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
       's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']
SPECIAL = {0x00: 'sll', 0x02: 'srl', 0x03: 'sra', 0x08: 'jr', 0x09: 'jalr', 0x18: 'mult', 0x1A: 'div',
           0x10: 'mfhi', 0x12: 'mflo', 0x20: 'add', 0x21: 'addu', 0x23: 'subu', 0x24: 'and', 0x25: 'or',
           0x26: 'xor', 0x2A: 'slt', 0x2B: 'sltu'}
IMM = {0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu', 0x0C: 'andi', 0x0D: 'ori', 0x0E: 'xori',
       0x0F: 'lui', 0x04: 'beq', 0x05: 'bne', 0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu',
       0x28: 'sb', 0x29: 'sh', 0x2B: 'sw', 0x2F: 'cache'}

with open(iso, 'rb') as f:
    for va in range(va0, va1, 4):
        f.seek(va - BIAS)
        w = struct.unpack('<I', f.read(4))[0]
        op = w >> 26
        rs, rt, rd, sa, fn = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31, (w >> 6) & 31, w & 63
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        if op == 0:
            txt = '%-6s %s, %s, %s' % (SPECIAL.get(fn, '?%02X' % fn), REG[rd], REG[rs], REG[rt])
            if fn in (0x00, 0x02, 0x03):
                txt = '%-6s %s, %s, %d' % (SPECIAL[fn], REG[rd], REG[rt], sa)
            if fn in (0x10, 0x12):
                txt = '%-6s %s' % (SPECIAL[fn], REG[rd])
        elif op in IMM:
            txt = '%-6s %s, %s, %d (0x%X)' % (IMM[op], REG[rt], REG[rs], simm, imm)
        else:
            txt = 'op=%02X raw=0x%08X' % (op, w)
        print('  %08X  %08X  %s' % (va, w, txt))
