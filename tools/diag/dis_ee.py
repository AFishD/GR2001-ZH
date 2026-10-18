# -*- coding: utf-8 -*-
r"""dis.py — 通用 EE 反汇编 (会话工具): python dis.py <elf文件> <hexVA> [字节数]
(从 work/builds/GR_ZH72/temp/dis4t.py 提取, 去掉硬编码路径)"""
import bisect
import os
import re
import struct
import sys

SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00
R = ['$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3', '$t0', '$t1', '$t2', '$t3',
     '$t4', '$t5', '$t6', '$t7', '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
     '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra']
FR = ['$f%d' % i for i in range(32)]


def si(x):
    return x - 0x10000 if x >= 0x8000 else x


def build(path):
    data = open(path, 'rb').read()
    main = data[SEC_OFF:SEC_OFF + SEC_SIZE]
    strtab = data[0x4DEDE0:0x4DEDE0 + 0x13E199]
    syms = {}
    p, end = 0x61CF80, 0x61CF80 + 0x97420
    while p < end and p + 16 <= len(data):
        name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p)
        p += 16
        if name and value and SEC_ADDR <= value < SEC_ADDR + SEC_SIZE:
            n = strtab[name:strtab.index(b'\0', name)].decode('latin-1')
            syms.setdefault(value, n)
    return data, main, syms, sorted(syms)


def fname(syms, keys, va):
    i = bisect.bisect_right(keys, va) - 1
    if i >= 0:
        k = keys[i]
        if 0 <= va - k < 0x8000:
            return '%s+0x%X' % (syms[k], va - k)
    return 'sub_%08X' % va


def main():
    elf, va = sys.argv[1], int(sys.argv[2], 16)
    ln = int(sys.argv[3], 0) if len(sys.argv) > 3 else 200
    data, seg, syms, keys = build(elf)
    for a in range(0, ln, 4):
        off = va - SEC_ADDR + a
        if off < 0 or off + 4 > len(seg):
            break
        w = struct.unpack_from('<I', seg, off)[0]
        op = w >> 26
        rs, rt, rd = (w >> 21) & 31, (w >> 16) & 31, (w >> 11) & 31
        sa, fn = (w >> 6) & 31, w & 63
        imm = si(w & 0xFFFF)
        if w == 0:
            s = 'nop'
        elif op == 0:
            tbl = {0x21: 'addu', 0x23: 'subu', 0x20: 'add', 0x22: 'sub', 0x24: 'and', 0x25: 'or',
                   0x2A: 'slt', 0x2B: 'sltu', 0x08: 'jr', 0x09: 'jalr', 0x00: 'sll', 0x02: 'srl',
                   0x03: 'sra', 0x18: 'mult', 0x1A: 'div', 0x10: 'mfhi', 0x12: 'mflo'}
            n = tbl.get(fn)
            if fn == 0x08:
                s = 'jr %s' % R[rs]
            elif fn in (0x00, 0x02, 0x03):
                s = '%s %s, %s, %d' % (n, R[rd], R[rt], sa)
            elif n:
                s = '%s %s, %s, %s' % (n, R[rd], R[rs], R[rt])
            else:
                s = '.word %08X' % w
        elif op in (2, 3):
            tgt = (w & 0x3FFFFFF) << 2
            s = '%s 0x%08X  (%s)' % ('jal' if op == 3 else 'j', tgt, fname(syms, keys, tgt))
        elif op == 4:
            s = 'beq %s, %s, 0x%08X' % (R[rs], R[rt], va + a + 4 + (imm << 2))
        elif op == 5:
            s = 'bne %s, %s, 0x%08X' % (R[rs], R[rt], va + a + 4 + (imm << 2))
        elif op == 1:
            s = 'bltz/bgez %s, 0x%08X' % (R[rs], va + a + 4 + (imm << 2))
        elif op == 0x0F:
            s = 'lui %s, 0x%04X' % (R[rt], w & 0xFFFF)
        elif op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E):
            tbl = {8: 'addi', 9: 'addiu', 0xA: 'slti', 0xB: 'sltiu', 0xC: 'andi', 0xD: 'ori', 0xE: 'xori'}
            s = '%s %s, %s, %d' % (tbl[op], R[rt], R[rs], imm)
        elif op in (0x20, 0x21, 0x23, 0x24, 0x25, 0x2B):
            tbl = {0x20: 'lb', 0x21: 'lh', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu', 0x2B: 'sw'}
            s = '%s %s, %d(%s)' % (tbl[op], R[rt], imm, R[rs])
        else:
            s = '.word %08X' % w
        print('%08X  %s' % (va + a, s))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
