# -*- coding: utf-8 -*-
r"""fix_zh116_dis.py — 极简 MIPS (R5900) 反汇编 + EE RAM 区域 dump/对比

用法:
  python tools/iso_build/fix_zh116_dis.py <eeram.bin> --at 0x00081FC0 [--n 60]
  python tools/iso_build/fix_zh116_dis.py <eeram.bin> --hex 0x00081F00 0x200
  python tools/iso_build/fix_zh116_dis.py <eeram.bin> --diff <other.bin> 0x00081F00 0x200
"""
import argparse
import struct
import sys

SPECIAL = {0x00: 'sll', 0x02: 'srl', 0x03: 'sra', 0x04: 'sllv', 0x06: 'srlv', 0x07: 'srav',
           0x08: 'jr', 0x09: 'jalr', 0x0C: 'syscall', 0x0D: 'break', 0x0F: 'sync',
           0x10: 'mfhi', 0x11: 'mthi', 0x12: 'mflo', 0x13: 'mtlo', 0x18: 'mult', 0x19: 'multu',
           0x1A: 'div', 0x1B: 'divu', 0x20: 'add', 0x21: 'addu', 0x22: 'sub', 0x23: 'subu',
           0x24: 'and', 0x25: 'or', 0x26: 'xor', 0x27: 'nor', 0x2A: 'slt', 0x2B: 'sltu'}
REGIMM = {0x00: 'bltz', 0x01: 'bgez', 0x10: 'bltzal', 0x11: 'bgezal'}
OPC = {0x01: 'REGIMM', 0x02: 'j', 0x03: 'jal', 0x04: 'beq', 0x05: 'bne', 0x06: 'blez', 0x07: 'bgtz',
       0x08: 'addi', 0x09: 'addiu', 0x0A: 'slti', 0x0B: 'sltiu', 0x0C: 'andi', 0x0D: 'ori',
       0x0E: 'xori', 0x0F: 'lui', 0x10: 'cop0', 0x11: 'cop1', 0x14: 'beql', 0x15: 'bnel',
       0x16: 'blezl', 0x17: 'bgtzl', 0x18: 'daddi', 0x19: 'daddiu', 0x1A: 'ldl', 0x1B: 'ldr',
       0x20: 'lb', 0x21: 'lh', 0x22: 'lwl', 0x23: 'lw', 0x24: 'lbu', 0x25: 'lhu', 0x26: 'lwr',
       0x27: 'lwu', 0x28: 'sb', 0x29: 'sh', 0x2A: 'swl', 0x2B: 'sw', 0x2C: 'sdl', 0x2D: 'sdr',
       0x2E: 'swr', 0x2F: 'cache', 0x31: 'lwc1', 0x39: 'swc1', 0x1F: 'sq', 0x37: 'ld'}
LOADS = {'lb', 'lh', 'lw', 'lbu', 'lhu', 'lwu', 'ld', 'lwl', 'lwr', 'ldl', 'ldr'}
STORES = {'sb', 'sh', 'sw', 'swl', 'swr', 'sdl', 'sdr', 'sq', 'cache'}


def s16(v):
    return v - 0x10000 if v & 0x8000 else v


def dis1(pc, w):
    op = w >> 26
    rs = (w >> 21) & 31
    rt = (w >> 16) & 31
    rd = (w >> 11) & 31
    sa = (w >> 6) & 31
    fn = w & 63
    imm = w & 0xFFFF
    if w == 0:
        return 'nop'
    if op == 0:
        if fn in (0x08,):
            return 'jr $%d' % rs
        if fn == 0x09:
            return 'jalr $%d, $%d' % (rd, rs)
        if fn in (0x00, 0x02, 0x03):
            return '%s $%d, $%d, %d' % (SPECIAL[fn], rd, rt, sa)
        if fn in (0x10, 0x12):
            return '%s $%d' % (SPECIAL[fn], rd)
        if fn in (0x11, 0x13, 0x18, 0x19, 0x1A, 0x1B):
            return '%s $%d, $%d' % (SPECIAL[fn], rs, rt)
        if fn in (0x0C, 0x0D):
            return SPECIAL[fn]
        if fn in (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x2A, 0x2B):
            return '%s $%d, $%d, $%d' % (SPECIAL[fn], rd, rs, rt)
        return 'special %02X' % fn
    if op == 1:
        name = REGIMM.get(rt, 'regimm%02X' % rt)
        tgt = pc + 4 + (s16(imm) << 2)
        return '%s $%d, %08X' % (name, rs, tgt)
    if op in (2, 3):
        return '%s %08X' % (OPC[op], ((pc + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
    if op in (4, 5, 0x14, 0x15):
        tgt = pc + 4 + (s16(imm) << 2)
        return '%s $%d, $%d, %08X' % (OPC[op], rs, rt, tgt)
    if op in (6, 7, 0x16, 0x17):
        tgt = pc + 4 + (s16(imm) << 2)
        return '%s $%d, %08X' % (OPC[op], rs, tgt)
    if op in (8, 9, 0xA, 0xB, 0xC, 0xD, 0xE):
        return '%s $%d, $%d, %d' % (OPC[op], rt, rs, s16(imm))
    if op == 0x0F:
        return 'lui $%d, %04X' % (rt, imm)
    if op in (0x18, 0x19):
        return '%s $%d, $%d, %d' % (OPC[op], rt, rs, s16(imm))
    name = OPC.get(op, 'op%02X' % op)
    if name in LOADS or name in STORES:
        return '%s $%d, %d($%d)' % (name, rt, s16(imm), rs)
    return '%s %04X' % (name, imm)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ram')
    ap.add_argument('--at', default=None)
    ap.add_argument('--n', type=int, default=48)
    ap.add_argument('--hex', nargs=2, default=None, metavar=('ADDR', 'LEN'))
    ap.add_argument('--diff', default=None)
    a = ap.parse_args()
    d = open(a.ram, 'rb').read()
    if a.hex:
        addr = int(a.hex[0], 0)
        ln = int(a.hex[1], 0)
        for i in range(0, ln, 16):
            row = d[addr + i:addr + i + 16]
            print('%08X  %s' % (addr + i, ' '.join('%02X' % b for b in row)))
    if a.diff:
        o = open(a.diff, 'rb').read()
        addr = int(a.hex[0], 0) if a.hex else 0
        ln = int(a.hex[1], 0) if a.hex else 0x100
        n = 0
        for i in range(ln):
            if d[addr + i] != o[addr + i]:
                if n < 64:
                    print('%08X  this=%02X other=%02X' % (addr + i, d[addr + i], o[addr + i]))
                n += 1
        print('differing bytes: %d / %d' % (n, ln))
    if a.at:
        pc = int(a.at, 0)
        for i in range(a.n):
            w = struct.unpack_from('<I', d, pc + i * 4)[0]
            print('%08X  %08X  %s' % (pc + i * 4, w, dis1(pc + i * 4, w)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
