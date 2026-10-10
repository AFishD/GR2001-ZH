# -*- coding: utf-8 -*-
r"""patch_zh72.py — GR_ZH72 = ZH70 + 大小写折叠循环高字节守卫 (纯 ELF 补丁, 12 词)

问题 (PROGRESS §36→§37 定案): 小队兵种字段显示 ' 突击向\t' — 真根因不是套件指针、
不是字库、不是 RES, 而是原版引擎的大小写折叠循环 (与 EN 逐字节同, 原生潜伏缺陷):

  RSUIString::LowerCase 0x53FF80 → 循环 0x407060: 逐字节 c 查 0x585961+(s8)c 处的
  ctype 标志表, bit0=1 则 c += 0x20。表按**符号扩展**索引: ASCII(<0x80) 落在真表
  0x585961-0x5859E0 (A-Z=01, a-z=02 …, 正确); zh16 高字节 (≥0x80) 索引变负, 落进
  表**下方**的 rodata 字符串 ("01_CAVES.mis"/"p:\ike\releases"/"please"/"logo"/
  assertion 格串), 撞上奇字节即被 +0x20 (mod 256):
      队 C1→E1 (=向!), 员 E9→09 (=TAB), F6→16 (ZH71 对偶编码实测) …
  组装器 0x30EE8C 对兵种名 Substring(1) 调 LowerCase ("首字符大写其余小写" 整形),
  ZH70 组装记录 ' 突击队员'(20 A2B6 B6 C1 E9) 被写成 20 A2B6 B6 E1 09 → 字段渲染
  成 ' 突击向\t'。EN 全 ASCII 永不触发。同型 UpperCase 循环 0x408910 (bit1, -0x20)
  同病: 高字节撞上 bit1 字节会被 -0x20。
  只读的大小写不敏感比较 0x406950 无回写 (双侧同折, 语义不变), 不修; 其余 12 处
  表引用为纯位测试 (isdigit/isspace…), 高字节误判无破坏性, 不修。

修复 (同足迹守卫, 每循环 6 词, 无新 cave, ASCII 语义逐位不变):
  c >= 0x80 → 直接跳过折叠 (zh16 无大小写); c < 0x80 → 零扩展索引 = 原地址不变。
  查表临时寄存器改用 t0 (两函数均为无栈叶函数, 原码未用 t0; a1 不再被覆写, 只增安全性)。
  0x407060 调用者 3 处 (RSUIString::LowerCase 尾 0x540038 等)、0x408910 调用者 8 处
  (RSUIString::UpperCase 0x540118 等) 全部受益。

验证纪律: 12 词原始值硬断言; 全盘差异白名单 = 4 个词窗口; 往返反汇编 (lbu 编码
0x24 误 0x25 曾被反汇编器逮住: 表基址奇数, lhu 偶偏移非对齐会地址错误)。

用法: python patch_zh72.py <src_iso> <dst_iso>   (基底 = GR_ZH70)
"""
import os
import shutil
import struct
import sys

ELF_LBA = 295
SEC_OFF, SEC_ADDR = 0x80, 0x00100000  # phdr0: vaddr 0x100000 @ file 0x80

# (VA, 期望原始词, 新词)  — 编码见模块内函数注释, 已过 dis4t72.py 反汇编往返
AT, V0, V1, A3, T0 = 1, 2, 3, 7, 8


def enc_r(rs, rt, rd, sa, fn):
    return (rs << 21) | (rt << 16) | (rd << 11) | (sa << 6) | fn


def enc_i(op, rs, rt, imm):
    return (op << 26) | (rs << 21) | (rt << 16) | (imm & 0xFFFF)


GUARD = enc_i(0x0B, V1, AT, 0x80)      # sltiu at, v1, 0x80   (c<0x80?)
SKIP = enc_i(0x04, AT, 0, 7)           # beq   at, zero, +7   (c>=0x80 → 跳过折叠)
TBASE = enc_i(0x09, A3, T0, 0x5961)    # addiu t0, a3, 0x5961 (表基址)
TINDEX = enc_r(V1, T0, T0, 0, 0x21)    # addu  t0, v1, t0     (零扩展索引, ASCII 地址不变)
TLOAD = enc_i(0x24, T0, V0, 0)         # lbu   v0, 0(t0)      (0x24=lbu; 0x25=lhu 会非对齐!)
FOLD_LO = enc_i(0x09, V1, V0, 0x20)    # addiu v0, v1, 0x20   (lower)
FOLD_UP = enc_i(0x09, V1, V0, 0xFFE0)  # addiu v0, v1, -0x20  (upper)

WORDS = [
    # LowerCase 循环 0x407060: sign-extend 查表 → 高字节守卫 + 零扩展索引
    (0x407078, 0x00031600, GUARD),    # sll v0,v1,24      -> sltiu at,v1,0x80
    (0x40707C, 0x00022E03, SKIP),      # sra a1,v0,24      -> beq at,0,skip
    (0x407080, 0x24E35961, TBASE),    # addiu v1,a3,0x5961 -> addiu t0,a3,0x5961
    (0x407084, 0x00A31821, TINDEX),   # addu v1,a1,v1     -> addu t0,v1,t0
    (0x407088, 0x90620000, TLOAD),    # lbu v0,0(v1)      -> lbu v0,0(t0)
    (0x407094, 0x24A20020, FOLD_LO),  # addiu v0,a1,0x20  -> addiu v0,v1,0x20
    # UpperCase 循环 0x408910: 同型
    (0x408928, 0x00031600, GUARD),
    (0x40892C, 0x00022E03, SKIP),
    (0x408930, 0x24E35961, TBASE),
    (0x408934, 0x00A31821, TINDEX),
    (0x408938, 0x90620000, TLOAD),
    (0x408944, 0x24A2FFE0, FOLD_UP),
]


def main(src, dst):
    shutil.copyfile(src, dst)
    base = ELF_LBA * 2048
    with open(dst, 'r+b') as f:
        f.seek(base)
        assert f.read(4) == b'\x7fELF', 'SLUS ELF 魔数错位 (LBA=%d?)' % ELF_LBA
        f.seek(base + 0x1C)
        phoff = struct.unpack('<I', f.read(4))[0]
        f.seek(base + phoff)
        p_type, p_offset, p_vaddr = struct.unpack('<III', f.read(12))
        assert (p_type, p_offset, p_vaddr) == (1, SEC_OFF, SEC_ADDR), \
            'phdr0 与 ZH70 不符: %r' % ((p_type, p_offset, p_vaddr),)
        for va, orig, new in WORDS:
            f.seek(base + SEC_OFF + (va - SEC_ADDR))
            cur = struct.unpack('<I', f.read(4))[0]
            assert cur == orig, '%06X: %08X != 原始 %08X (基底不是 ZH70?)' % (va, cur, orig)
            f.seek(base + SEC_OFF + (va - SEC_ADDR))
            f.write(struct.pack('<I', new))
        print('[elf] 大小写折叠守卫 12 词落盘 (0x407078 区 6 词 + 0x408928 区 6 词)')
    # 全盘白名单差分: 只许 4 个窗口内有差 (连续 5 词 + 孤立 1 词) × 两个循环
    win = []
    for va, ln in ((0x407078, 0x14), (0x407094, 4), (0x408928, 0x14), (0x408944, 4)):
        win.append((base + SEC_OFF + (va - SEC_ADDR), ln))
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, bad = 0, []
    while True:
        ca, cb = a.read(1 << 20), b.read(1 << 20)
        if not ca:
            break
        for i in range(len(ca)):
            if ca[i] != cb[i]:
                p = pos + i
                if not any(o <= p < o + l for o, l in win):
                    bad.append(p)
        pos += len(ca)
    a.close()
    b.close()
    assert not bad, '窗口外差异 ' + repr([hex(x) for x in bad[:5]])
    print('[diff] 差异全部位于 12 词守卫窗口 ✓ (纯 ELF 补丁, 48B)')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
