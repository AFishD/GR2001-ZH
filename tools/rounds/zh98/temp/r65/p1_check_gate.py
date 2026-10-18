# -*- coding: utf-8 -*-
r"""p1_check_gate.py — 现役盘 GR_ZH109 的 ELF 里, DBCS lead gate 到底是 0xAE 还是 0xB1?

方法: 直接从 ISO 读 ELF (无需解包 —— ELF 在 LBA 295, 段偏移 0x80, VA 基址 0x00100000),
      ① 点名看 方案 C 的 4 个站点 (0x416EE8 / 0x417160 / 0x41751C / 0x5656A4);
      ② 全段扫所有 slti/sltiu 且 imm ∈ lead 相关值, 看有没有第 5 处漏网的 gate。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..', '..'))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
ELF_SIZE = 0x500000

data = open(ISO, 'rb').read(ELF_LBA * 2048 + SEC_OFF + ELF_SIZE)
print('ISO      = %s (%d B)' % (ISO, os.path.getsize(ISO)))
print('ELF 段   = LBA %d + 0x%X, VA 0x%08X..0x%08X' % (ELF_LBA, SEC_OFF, SEC_ADDR, SEC_ADDR + ELF_SIZE))


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


def word(va):
    return struct.unpack_from('<I', data, elf_off(va))[0]


SITES = [0x416EE8, 0x417160, 0x41751C, 0x5656A4]
print('\n== 方案 C 的 4 个站点 ==')
for va in SITES:
    w = word(va)
    op = w >> 26
    imm = w & 0xFFFF
    print('  0x%06X  %08X  op=%02X(%s) rs=%d rt=%d imm=0x%X'
          % (va, w, op, 'sltiu' if op == 0x0B else ('slti' if op == 0x0A else '?'),
             (w >> 21) & 0x1F, (w >> 16) & 0x1F, imm))

print('\n== 之前 4 条指令的上下文 (确认是同一条 sltiu) ==')
for va in SITES:
    row = []
    for d in (-8, -4, 0, 4):
        row.append('%06X:%08X' % (va + d, word(va + d)))
    print('  ' + '  '.join(row))

IMMS = (0xA1, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB4, 0xFE, 0xFF)
hits = {}
for va in range(SEC_ADDR, SEC_ADDR + ELF_SIZE, 4):
    w = word(va)
    op = w >> 26
    if op not in (0x0A, 0x0B):
        continue
    imm = w & 0xFFFF
    if imm in IMMS:
        hits.setdefault(imm, []).append((va, w, op, (w >> 21) & 0x1F, (w >> 16) & 0x1F))
print('\n== 全段 slti/sltiu 站点 (imm ∈ lead 相关值) ==')
for imm in sorted(hits):
    lst = hits[imm]
    print('  imm=0x%02X : %d 处' % (imm, len(lst)))
    for (va, w, op, rs, rt) in lst:
        mark = ' ★' if va in SITES else ''
        print('     0x%06X  %08X  %s rs=%d rt=%d%s'
              % (va, w, 'slti ' if op == 0x0A else 'sltiu', rs, rt, mark))
