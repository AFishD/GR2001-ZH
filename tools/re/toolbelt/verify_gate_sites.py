# -*- coding: utf-8 -*-
r"""verify_gate_sites.py — 核验 4 个 gate 在 ISO 里的确切字节（为 gate 探针铺路）

独立来源: 前一个构建任务的 zero_verify_sites.py 报告
  0x416EE8 / 0x417160 / 0x41751C / 0x5656A4 = ISO 0x3AA768 / 0x3AA9E0 / 0x3AAD9C / 0x4F8F24
  全部应为 `sltiu …, 0xB1`（opcode 0x0B, imm 0x00B1）
本脚本: 直接读 ISO 逐处核对，并给出"改成 0xB7"后的字节。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SITES = [
    (0x416EE8, 0x3AA768),
    (0x417160, 0x3AA9E0),
    (0x41751C, 0x3AAD9C),
    (0x5656A4, 0x4F8F24),
]
REG = ['zero', 'at', 'v0', 'v1', 'a0', 'a1', 'a2', 'a3', 't0', 't1', 't2', 't3', 't4', 't5', 't6', 't7',
       's0', 's1', 's2', 's3', 's4', 's5', 's6', 's7', 't8', 't9', 'k0', 'k1', 'gp', 'sp', 'fp', 'ra']

data = open(ISO, 'rb').read()
print('ISO %s (%d B)' % (os.path.basename(ISO), len(data)))
print()
ok = 0
for va, off in SITES:
    w = struct.unpack_from('<I', data, off)[0]
    op = w >> 26
    rs = (w >> 21) & 31
    rt = (w >> 16) & 31
    imm = w & 0xFFFF
    name = 'sltiu' if op == 0x0B else ('op=0x%X' % op)
    good = (op == 0x0B and imm == 0xB1)
    if good:
        ok += 1
    new = (w & 0xFFFF0000) | 0xB7
    print('  VA 0x%08X  ISO 0x%08X  %08X  %s %s, %s, 0x%X (%d)  %s'
          % (va, off, w, name, REG[rt], REG[rs], imm, imm,
             '✓ 命中 sltiu …,0xB1' if good else '✗ 不符'))
    print('      体检修: 改为 0xB7 ⇒ %08X  (ISO 字节 %s → %s)'
          % (new, struct.pack('<I', w).hex(), struct.pack('<I', new).hex()))
print()
print('  ⇒ 4 处中 %d 处命中 ⇒ %s' % (ok, '与既有报告一致 ✓（gate 探针可以照此下针 ✓）' if ok == 4 else '与报告不一致 ✗（必须先查清再下针）'))
