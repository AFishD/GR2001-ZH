# -*- coding: utf-8 -*-
r"""verify_cave_pred.md — 反查 cave 0x417050 的对偶码分支: 记录分支是否恒不可达

依据(审计报告 F6): 判据 = `sltu (slot + 0xE0), nrec` ⇒ 对任意 slot ≥ 0 恒真 ⇒ 记录分支恒不执行。
本脚本: 从 ELF 里读出 cave 0x417050 起的一段机器码，人工可判地列出关键指令
        （sltiu/sltu/addiu/bne/beq/jal 等），核对是否存在 `slot+0xE0` 与 `nrec` 的比较。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r72', 'SLUS_206.13.elf')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ELF_OFF = 0x295 * 2048 + 0x80     # 见既有工具 find_lbn.py 的口径: 295*2048 + 0x80
VA_BASE = 0x100000                # ELF 头偏移 + VA 基准（VA - 0x100000）


def va2off(va):
    return ELF_OFF + (va - VA_BASE)


data = open(ELF, 'rb').read()

REG = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
       's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']


def dis(w, pc):
    op = w >> 26
    rs = (w >> 21) & 31
    rt = (w >> 16) & 31
    imm = w & 0xFFFF
    simm = imm - 0x10000 if imm & 0x8000 else imm
    if w == 0:
        return 'nop'
    if op == 0x0B:   # sltiu
        return 'sltiu  %s, %s, 0x%X (%d)' % (REG[rt], REG[rs], imm, imm)
    if op == 0x0A:   # slti
        return 'slti   %s, %s, %d' % (REG[rt], REG[rs], simm)
    if op == 0x09:   # addiu
        return 'addiu  %s, %s, %d' % (REG[rt], REG[rs], simm)
    if op == 0x0D:   # ori
        return 'ori    %s, %s, 0x%X' % (REG[rt], REG[rs], imm)
    if op == 0x0F:   # lui
        return 'lui    %s, 0x%X' % (REG[rt], imm)
    if op == 0x0C:   # andi
        return 'andi   %s, %s, 0x%X' % (REG[rt], REG[rs], imm)
    if op == 0x05:   # bne
        return 'bne    %s, %s, 0x%X' % (REG[rs], REG[rt], pc + 4 + simm * 4)
    if op == 0x04:   # beq
        return 'beq    %s, %s, 0x%X' % (REG[rs], REG[rt], pc + 4 + simm * 4)
    if op == 0x03:   # jal
        return 'jal    0x%X' % ((pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
    if op == 0x02:   # j
        return 'j      0x%X' % ((pc & 0xF0000000) | ((w & 0x3FFFFFF) << 2))
    if op == 0x23:   # lw
        return 'lw     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x2B:   # sw
        return 'sw     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x25:   # lhu
        return 'lhu    %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x27:   # lwu
        return 'lwu    %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x29:   # sh
        return 'sh     %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x24:   # lbu
        return 'lbu    %s, %d(%s)' % (REG[rt], simm, REG[rs])
    if op == 0x00 and (w & 0x3F) == 0x0D:
        return 'break/jalr? (SPECIAL 0x0D)'
    if op == 0x00 and (w & 0x3F) == 0x08:
        return 'jr     %s' % REG[rs]
    if op == 0x00 and (w & 0x3F) == 0x09:
        return 'jalr   %s' % REG[rs]
    if op == 0x00 and (w & 0x3F) == 0x21:
        return 'addu   %s, %s, %s' % (REG[(w >> 11) & 31], REG[rs], REG[rt])
    if op == 0x00 and (w & 0x3F) == 0x1A:
        return 'div    %s, %s' % (REG[rs], REG[rt])
    if op == 0x00 and (w & 0x3F) == 0x12:
        return 'mflo   %s' % REG[(w >> 11) & 31]
    if op == 0x00 and (w & 0x3F) == 0x18:
        return 'mult   %s, %s (R5900: rd=%s)' % (REG[rs], REG[rt], REG[(w >> 11) & 31])
    return '?? op=%d w=0x%08X' % (op, w)


print('ELF=%s' % ELF)
lo, hi = 0x417050, 0x4171E0
print('反汇编 cave 0x%X..0x%X :' % (lo, hi))
for va in range(lo, hi, 4):
    off = va2off(va)
    if off + 4 > len(data):
        break
    w = struct.unpack_from('<I', data, off)[0]
    line = dis(w, va)
    mark = ''
    if 'sltiu' in line or 'sltu' in line or '0xE0' in line or '224' in line:
        mark = '   ← ★'
    print('  0x%08X  %08X  %s%s' % (va, w, line, mark))
