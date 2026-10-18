# -*- coding: utf-8 -*-
r"""dump_decode_cave.py — 反汇编解码 cave（0x416ED0 起），找"单字节 vs 对偶"的真判据

偏移映射（用已核验的 gate 站点反推）:
  ISO = 0x937A0 + 0xE0 + (VA − 0x100000)
  验证: VA 0x416EE8 ⇒ 0x937A0 + 0xE0 + 0x316EE8 = 0x3AA768 ✓（与 verify_gate_sites.py 实测一致 ✓）
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 0x937A0 + 0xE0 - 0x100000     # ISO = BASE + VA


def va2off(va):
    return BASE + va


REG = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
       's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']


def dis(w, pc):
    op = w >> 26
    rs = (w >> 21) & 31
    rt = (w >> 16) & 31
    rd = (w >> 11) & 31
    sa = (w >> 6) & 31
    fn = w & 0x3F
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    if w == 0:
        return 'nop'
    if op == 0x0B:
        return 'sltiu  %s, %s, 0x%X (%d)   ★上界/下界判据' % (REG[rt], REG[rs], imm, imm)
    if op == 0x0A:
        return 'slti   %s, %s, %d' % (REG[rt], REG[rs], simm)
    if op == 0x09:
        return 'addiu  %s, %s, %d' % (REG[rt], REG[rs], simm)
    if op == 0x0C:
        return 'andi   %s, %s, 0x%X' % (REG[rt], REG[rs], imm)
    if op == 0x0D:
        return 'ori    %s, %s, 0x%X' % (REG[rt], REG[rs], imm)
    if op == 0x0F:
        return 'lui    %s, 0x%X' % (REG[rt], imm)
    if op == 0x05:
        return 'bne    %s, %s, 0x%X' % (REG[rs], REG[rt], (pc + 4 + simm * 4) & 0xFFFFFFFF)
    if op == 0x04:
        return 'beq    %s, %s, 0x%X' % (REG[rs], REG[rt], (pc + 4 + simm * 4) & 0xFFFFFFFF)
    if op == 0x03:
        return 'jal    0x%X' % ((pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
    if op == 0x02:
        return 'j      0x%X' % ((pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
    if op == 0x23:
        return 'lw     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x2B:
        return 'sw     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x25:
        return 'lhu    %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x29:
        return 'sh     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x24:
        return 'lbu    %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x28:
        return 'sb     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x00:
        if fn == 0x08:
            return 'jr     %s' % REG[rs]
        if fn == 0x09:
            return 'jalr   %s' % REG[rs]
        if fn == 0x21:
            return 'addu   %s, %s, %s' % (REG[rd], REG[rs], REG[rt])
        if fn == 0x23:
            return 'subu   %s, %s, %s' % (REG[rd], REG[rs], REG[rt])
        if fn == 0x2A:
            return 'slt    %s, %s, %s' % (REG[rd], REG[rs], REG[rt])
        if fn == 0x2B:
            return 'sltu   %s, %s, %s' % (REG[rd], REG[rs], REG[rt])
        if fn == 0x1A:
            return 'div    %s, %s' % (REG[rs], REG[rt])
        if fn == 0x10:
            return 'mfhi   %s' % REG[rd]
        if fn == 0x12:
            return 'mflo   %s' % REG[rd]
        if fn == 0x18:
            return 'mult   %s, %s (R5900 三操作数: rd=%s)' % (REG[rs], REG[rt], REG[rd])
        if fn == 0x00:
            return 'sll    %s, %s, %d' % (REG[rd], REG[rt], sa)
        if fn == 0x02:
            return 'srl    %s, %s, %d' % (REG[rd], REG[rt], sa)
    return '?? op=0x%X w=%08X' % (op, w)


data = open(ISO, 'rb').read()
print('校验映射: VA 0x416EE8 ⇒ ISO 0x%X（应为 0x3AA768）' % va2off(0x416EE8))
w = struct.unpack_from('<I', data, va2off(0x416EE8))[0]
print('  读出 = %08X ⇒ %s' % (w, '映射正确 ✓' if w == 0x2CA900B7 or w == 0x2CA900B1 else '映射错误 ✗'))
print()
lo, hi = 0x416ED0, 0x416F80
print('解码 cave 0x%X..0x%X:' % (lo, hi))
for va in range(lo, hi, 4):
    off = va2off(va)
    if off < 0 or off + 4 > len(data):
        break
    w = struct.unpack_from('<I', data, off)[0]
    line = dis(w, va)
    mark = '   ← ★★' if ('andi' in line or 'slti' in line or 'addiu' in line and '0x' in line) else ''
    print('  0x%08X  %08X  %s%s' % (va, w, line, mark))
