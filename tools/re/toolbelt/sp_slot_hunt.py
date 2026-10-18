# -*- coding: utf-8 -*-
r"""sp_slot_hunt.py — 在原版/汉化 ELF 里找"某个 sp 偏移"的所有引用

用途: 判定汉化把缓冲从 sp+223 挪到 sp+222（并改成写 2 字节）之后,
      **sp+222 是不是撞上了别人的栈槽** —— 这是"文本布局整数写进指针槽"的最可能机制。

做法: 反汇编指定函数范围, 收集所有"立即数型 sp 偏移"引用, 按偏移归组。
      也做原始字节扫描（addiu/lw/lhu/sb/sh/sw 的 imm 字段 == 目标值）作为兜底。
用法: python sp_slot_hunt.py <函数起> <函数止> <要查的偏移,逗号分隔(十进制)>
例:   python sp_slot_hunt.py 0x219A70 0x219F00 222,223,224,225
"""
import os
import re
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

SEG_VA, SEG_OFF = 0x100000, 0x80


def va2off(va):
    return SEG_OFF + (va - SEG_VA)


def elf(iso):
    return tcslib.Iso(iso).read(295 * 2048, 38057892 - 604160)


orig = elf(os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
mod = elf(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))

a = int(sys.argv[1], 0) if len(sys.argv) > 1 else 0x219A70
b = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x219F00
want = [int(x) for x in (sys.argv[3].split(',') if len(sys.argv) > 3 else ['222', '223', '224', '225'])]

# MIPS 立即数型指令里 "sp 相对偏移" 的识别：
#   0x27BD/0x2FBD/0x23BD/0x27BD... = addiu/lw/sw/lbu/sb/lhu/sh/ld/sd 且 rs==29($sp)
# 简化：解析出 opcode + rs + imm，rs==29 就视为 sp 相对
IMM_OPS = {
    0x23: 'lw', 0x2B: 'sw', 0x24: 'lbu', 0x28: 'sb', 0x25: 'lhu', 0x29: 'sh',
    0x27: 'lwu', 0x2F: 'sd', 0x37: 'ld', 0x0F: 'lui', 0x09: 'addiu', 0x0D: 'ori',
    0x20: 'lb', 0x21: 'lh',
}


def refs(buf, a, b, sp_only=True):
    out = {}
    for va in range(a, b, 4):
        k = va2off(va)
        if k + 4 > len(buf):
            break
        w = struct.unpack_from('<I', buf, k)[0]
        op = w >> 26
        rs = (w >> 21) & 0x1F
        rt = (w >> 16) & 0x1F
        imm = w & 0xFFFF
        if op not in IMM_OPS:
            continue
        if sp_only and rs != 29:
            continue
        s32 = imm - 0x10000 if imm & 0x8000 else imm
        for t in want:
            if s32 == t:
                out.setdefault(t, []).append((va, IMM_OPS[op], rt, s32))
    return out


print('函数范围 0x%08X..0x%08X ; 查询 sp 偏移 %s' % (a, b, want))
print()
for name, buf in (('原版 GR_EN_ORIG', orig), ('汉化 GR_ZH113b', mod)):
    r = refs(buf, a, b)
    print('=== %s ===' % name)
    for t in want:
        lst = r.get(t, [])
        print('  sp+%d : %d 处引用' % (t, len(lst)))
        for va, mn, rt, _ in lst[:12]:
            print('     0x%08X  %-6s $%d' % (va, mn, rt))
    print()
