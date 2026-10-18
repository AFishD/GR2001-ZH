# -*- coding: utf-8 -*-
r"""r72_dis2.py — 修正版反汇编器（补助记符 / 跳过 undecodable / 找函数入口与调用者）

修了 r72_dis.py 的两个毛病:
  ① 打印时漏了 ins.mnemonic（只有 bytes 与 op_str）
  ② capstone 碰到 R5900 的 MMI 等指令会 stop ⇒ 改为逐词解码, 解不出就前进 4 字节
新增:
  ③ 对每个 VA 回溯找"函数入口"（向前找最近的 jr $ra 之后的地址, 或 prologue 特征）
  ④ 全段搜 `jal <VA>` 调用者
"""
import struct
import sys

from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf'
SEG_VA, SEG_OFF = 0x100000, 0x80

elf = open(ELF, 'rb').read()
md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)


def va2off(va):
    return SEG_OFF + (va - SEG_VA)


def decode_range(va, nbytes):
    """逐词解码: capstone 解不出就跳 4 字节继续（避开 MMI 等）"""
    out = []
    off = va2off(va)
    end = off + nbytes
    o = off
    while o < end:
        got = list(md.disasm(elf[o:o + 4], va + (o - off)))
        if got:
            out.append(got[0])
        else:
            w = int.from_bytes(elf[o:o + 4], 'little')
            out.append(('RAW', va + (o - off), w))
        o += 4
    return out


def show(va, before=0x80, after=0x40, label=''):
    print('  ── %s VA=0x%08X ──' % (label, va))
    for it in decode_range(va - before, before + after):
        if isinstance(it, tuple):
            _, a, w = it
            print('     %08X  %08X  %-10s %s' % (a, w, '(未解码)', '<MMI/未知>' if w else ''))
            continue
        m = it.mnemonic
        mark = ''
        if m in ('jr', 'jalr'):
            mark = '   ★★★ 控制流!'
        elif m in ('jal', 'j'):
            mark = '   ★ 跳转'
        elif m.startswith('b') and m != 'break':
            mark = '   · 分支'
        cur = '  <<<<<< 崩溃点' if it.address == va else ''
        print('     %08X  %-8s %-9s %s%s%s' % (it.address, it.bytes.hex(), m, it.op_str, mark, cur))
    print()


VAS = [
    (0x102220, '反复 store 到 0x10b2bef8'),
    (0x101E6C, 'store 到 0x10b2bef8'),
    (0x101DE4, '从 0x10b2bf00 load'),
    (0x12BD00, '读垃圾指针 0xdb770d05…'),
    (0x12BD2C, '读垃圾指针 0x02020202/0xc'),
    (0x3F6038, '从地址 0 读'),
]
for va, why in VAS:
    show(va, 0x80, 0x30, why)

print('=== 找函数入口 (向前找 prologue: addiu $sp,$sp,-N) ===')
for va, why in VAS:
    off = va2off(va)
    found = None
    for k in range(0, 0x800, 4):
        o = off - k
        if o < SEG_OFF:
            break
        w = int.from_bytes(elf[o:o + 4], 'little')
        # addiu $sp,$sp,-imm  = 0x27BDFxxx ; sd ra,x(sp) 常见
        if (w & 0xFFFF0000) == 0x27BD0000 and (w & 0x8000):
            found = va - k
            break
    print('  0x%08X → 函数入口约 0x%08X (%s)' % (va, found if found else 0, why))

print()
print('=== 搜 jal <目标> 调用者 ===')
n = (len(elf) - SEG_OFF) // 4
words = struct.unpack_from('<%dI' % n, elf, SEG_OFF)
for tva, why in VAS:
    callers = []
    for i in range(n):
        w = words[i]
        if (w >> 26) == 0x03:                      # jal
            tgt = ((SEG_VA + i * 4) & 0xF0000000) | ((w & 0x03FFFFFF) << 2)
            if tgt == tva:
                callers.append(SEG_VA + i * 4)
    print('  0x%08X : %d 个 jal 调用者 %s' % (tva, len(callers), ['0x%08X' % c for c in callers[:6]]))
