# -*- coding: utf-8 -*-
r"""m23_scan_gates.py — 全 ELF 扫所有 "sltiu/slti ..., imm" 且 imm ∈ {0xA1,0xAD,0xAE,0xAF,0xB0,0xB4}
的站点, 确认 lead 判定到底有几处 (方案 C 只改了 4 处)。
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
ELF_LBA, SEC_OFF, SEC_ADDR = 295, 0x80, 0x00100000
ELF_SIZE = 0x500000
data = open(ISO, 'rb').read(ELF_LBA * 2048 + SEC_OFF + ELF_SIZE)


def elf_off(va):
    return ELF_LBA * 2048 + SEC_OFF + (va - SEC_ADDR)


IMMS = (0xA1, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB4, 0xFE, 0xFF)
print('== sltiu/slti 站点 (imm 落在 lead 相关值) ==')
hits = {}
for va in range(SEC_ADDR, SEC_ADDR + ELF_SIZE, 4):
    o = elf_off(va)
    if o + 4 > len(data):
        break
    w = struct.unpack_from('<I', data, o)[0]
    op = w >> 26
    if op not in (0x0A, 0x0B):          # slti / sltiu
        continue
    imm = w & 0xFFFF
    if imm in IMMS:
        hits.setdefault(imm, []).append((va, w, op, (w >> 21) & 0x1F, (w >> 16) & 0x1F))
for imm in sorted(hits):
    lst = hits[imm]
    print('  imm=0x%02X : %d 处' % (imm, len(lst)))
    for (va, w, op, rs, rt) in lst[:24]:
        print('     0x%06X  %08X  %s rs=%d rt=%d' % (va, w, 'slti' if op == 0x0A else 'sltiu', rs, rt))
    if len(lst) > 24:
        print('     ... 另 %d 处' % (len(lst) - 24))

print()
print('== 0xAE / 0xAF 作为立即数出现在任何指令里 (ori/andi/addiu/sltiu...) ==')
for target in (0xAE, 0xAF):
    cnt = 0
    samples = []
    for va in range(SEC_ADDR, SEC_ADDR + ELF_SIZE, 4):
        o = elf_off(va)
        w = struct.unpack_from('<I', data, o)[0]
        if (w & 0xFFFF) == target:
            cnt += 1
            if len(samples) < 14:
                samples.append((va, w))
    print('  imm=0x%02X 的指令 %d 条: %s' % (target, cnt, ' '.join('0x%06X:%08X' % s for s in samples)))
