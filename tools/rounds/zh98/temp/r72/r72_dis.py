# -*- coding: utf-8 -*-
r"""r72_dis.py — 反汇编 recLUT 崩溃相关的地址（capstone / MIPS R5900 little-endian）

目标: 回答"谁跳到 0x0CAC6800 / 那些垃圾指针从哪来"
  · 逐个反汇编崩溃链里出现过的 VA（±前后若干字节）
  · 标出控制流指令（jr/jalr/jal/j/branch）
  · 在 ELF 全文里搜"构造 0x10b2bef8 与 0x0cac6800 的立即数对"（lui+addiu/ori）
用法: python r72_dis.py <elf> [--va 0x...] ...
"""
import struct
import sys

from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ELF = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH98\temp\r72\SLUS_206.13.elf'
# 主段: VA 0x100000 起, 文件偏移 0x80 起(既有的补丁脚本口径)
SEG_VA = 0x100000
SEG_OFF = 0x80
SEG_LEN = 38057892 - 604160

md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 + CS_MODE_LITTLE_ENDIAN)
md.detail = False


def va2off(va):
    return SEG_OFF + (va - SEG_VA)


def dis(va, before=0x60, after=0x40, label=''):
    off = va2off(va - before)
    code = elf[off:off + before + after]
    print('  ── %s VA=0x%08X (文件偏移 0x%X) ──' % (label or '', va, off))
    for ins in md.disasm(code, va - before):
        mark = ''
        m = ins.mnemonic
        if m in ('jr', 'jalr'):
            mark = '   ★★★ 控制流'
        elif m in ('jal', 'j'):
            mark = '   ★ 跳转'
        elif m.startswith('b') and m not in ('break',):
            mark = '   · 分支'
        cur = ' <<<' if ins.address == va else ''
        print('     %08X  %-9s %-24s%s%s' % (ins.address, ins.bytes.hex(), ins.op_str, mark, cur))
    print()


elf = open(ELF, 'rb').read()
print('ELF %d B ; entry=0x%08X' % (len(elf), int.from_bytes(elf[0x18:0x1C], 'little')))
print()

# 崩溃链里出现过的关键 VA
VAS = [
    (0x102220, '反复 store 到 0x10b2bef8 的主循环'),
    (0x1024e8, '同上的另一个入口'),
    (0x101de4, '从 0x10b2bf00 load'),
    (0x101e6c, 'store 到 0x10b2bef8'),
    (0x12bd00, '读垃圾指针 0xdb770d05/0x74d7432f/0xd48a4250'),
    (0x12bd2c, '读垃圾指针 0x02020202 / 0xc'),
    (0x3f6038, '从地址 0 读'),
]
for va, why in VAS:
    print('  ▶ 0x%08X  (%s)' % (va, why))
    dis(va, 0x70, 0x30, why)

# 搜"谁构造了这些地址": lui + (addiu/ori) 立即数对上
print('=== 搜立即数构造 (lui hi + addiu/ori lo) ===')
targets = [0x10B2BEF8, 0x10B2BF00, 0x0CAC6800, 0x00000000, 0x02020202]
# 先线性反汇编整个主段(可能较慢, 只做一次) —— 这里用简化办法: 只扫 lui 指令, 再看其后 4 条内是否拼出目标
n = min(SEG_LEN, len(elf) - SEG_OFF) // 4
hits = {t: [] for t in targets}
words = struct.unpack_from('<%dI' % n, elf, SEG_OFF)
for i in range(n - 6):
    w = words[i]
    if (w >> 26) != 0x0F:           # lui
        continue
    rt = (w >> 16) & 0x1F
    hi = w & 0xFFFF
    for k in range(1, 6):
        w2 = words[i + k]
        op = w2 >> 26
        if op not in (0x09, 0x0D):   # addiu / ori
            continue
        rs2 = (w2 >> 21) & 0x1F
        rt2 = (w2 >> 16) & 0x1F
        lo = w2 & 0xFFFF
        if rs2 != rt or rt2 != rt:
            continue
        if op == 0x09:
            val = ((hi << 16) + (lo - 0x10000 if lo & 0x8000 else lo)) & 0xFFFFFFFF
        else:
            val = ((hi << 16) | lo) & 0xFFFFFFFF
        for t in targets:
            if val == t:
                hits[t].append((SEG_VA + i * 4, SEG_VA + (i + k) * 4))
for t in targets:
    print('  0x%08X : %d 处构造' % (t, len(hits[t])))
    for a, b in hits[t][:8]:
        print('     lui@0x%08X + op@0x%08X' % (a, b))
