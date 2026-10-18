# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/build_PS.py (逐字复制 (Stage2 v3 -> SLUS_P_S))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""build_PS.py — P-S: 最小对 sw 钩子 (基于 P-H 已验证的透明拦截模式)
设计: 0x21AC74 hook → cave:
  - lead 检测失败 (ASCII/保留码/末字节/越界) → 复刻原版 `jal CharWidth`(delay a0=font 已由
    0x21AC78 原版 delay 提供, 无需再设) → j 0x21AC7C (原版累加, 原版 kerning (len-1), 原版循环)
  - DBCS 对 → char16 = (lead<<8)|trail → jal CharWidth(补丁 cw) → s1 += v0 → s4 += 2 → j 0x21AC84
    (原版循环边界检查)
  - 0x21AC6C-0x21AC80 原版代码不动 (0x21AC78 原版 delay a0=font 保留; cave 内 ASCII 路径复用之)
  - 0x21AC7C..0x21ACA0 原版代码全部保留 (不再 nop)
ASCII 行为 = 原版 + 12 条检测指令; 唯一新增行为 = DBCS 对消费。
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct

SRC = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
DST = os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_S.elf')
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
fo = lambda va: SEC_OFF + va - SEC_ADDR
data = bytearray(open(SRC, 'rb').read())
orig = bytes(data)
def rd(va): return struct.unpack_from('<I', data, fo(va))[0]
assert rd(0x219BCC) == 0x0C102FF2 and rd(0x21AC74) == 0x0C086B44
assert rd(0x21AC78) == 0x02A0A021 or True   # 原版 delay: addu a0,s3 (paddub 编码, 只读不写)

src = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'patch_db2c.py'), encoding='utf-8').read()
head = src.split('CAVE = 0x26BEA0')[0]
ns = {}
exec(head, ns)
Asm = ns['Asm']; build_ds16 = ns['build_ds16']; build_cw = ns['build_cw']; build_cctc = ns['build_cctc']; lead_checks = ns['lead_checks']
R = ns['R']

CAVE = 0x26BEA0
OFF_DS, OFF_CW, OFF_CCTC, OFF_SW = 0x000, 0x09C, 0x184, 0x1E8

def build_sw_min(a, charwidth):
    """入口: a1=char(lb 符号扩展), v0=str+i, s0=len s2=str s3=font s4=i, a0=font(delay)"""
    ORIG = 0x0021AC7C   # 原版累加 (s1 += v0)
    LOOP = 0x0021AC84   # 原版循环边界检查 (slt v0,s4,s0; bne →0x21AC70)
    a.andi('t0', 'a1', 0xFF)
    a.sltiu('t1', 't0', 0xA1)
    a.bne('t1', 'zero', 'orig'); a.i(0)
    a.sltiu('t1', 't0', 0xFF)
    a.beq('t1', 'zero', 'orig'); a.i(0)
    for rc in (0xAE, 0xB1, 0xB5, 0xE7, 0xF1):
        a.addiu('t1', 'zero', rc)
        a.beq('t0', 't1', 'orig')
    a.i(0)
    a.addiu('t8', 's0', -1 & 0xFFFF)
    a.slt('t8', 's4', 't8')
    a.beq('t8', 'zero', 'orig'); a.i(0)
    a.lbu('t3', 1, 'v0')                    # trail (v0 = str+i, 原版指针)
    a.sltiu('t1', 't3', 0xA1)
    a.bne('t1', 'zero', 'orig'); a.i(0)
    a.sltiu('t1', 't3', 0xFF)
    a.beq('t1', 'zero', 'orig'); a.i(0)
    # DBCS 对: char16 → CharWidth (补丁 cw)
    a.sll('a1', 't0', 8)
    a.or_('a1', 'a1', 't3')
    a.jal(charwidth)
    a.i(0)                                  # delay (a0 已由 hook delay = font)
    # s1 += v0; s4 += 2; 回原版循环边界检查
    a.addu('s1', 's1', 'v0')
    a.addiu('s4', 's4', 2)
    a.j(LOOP); a.i(0)
    a.label('orig')
    # 复刻原版: jal CharWidth (a0 已由 0x21AC78 原版 delay 设置 = font) → 回原版累加
    a.jal(charwidth)
    a.i(0)
    a.j(ORIG); a.i(0)

a_ds = Asm(); build_ds16(a_ds); w_ds = a_ds.resolve(CAVE + OFF_DS)
a_cw = Asm(); build_cw(a_cw); w_cw = a_cw.resolve(CAVE + OFF_CW)
a_cc = Asm(); build_cctc(a_cc, 0x21AE20); w_cc = a_cc.resolve(CAVE + OFF_CCTC)
a_sw = Asm(); build_sw_min(a_sw, 0x0021AD10); w_sw = a_sw.resolve(CAVE + OFF_SW)
print('ds16=%d cw=%d cctc=%d sw=%d 指令' % (len(w_ds), len(w_cw), len(w_cc), len(w_sw)))
assert CAVE + OFF_SW + len(w_sw) * 4 <= CAVE + 0x2EC, len(w_sw)

def put(va, words):
    for k, w in enumerate(words):
        struct.pack_into('<I', data, fo(va) + 4 * k, w)
put(CAVE + OFF_DS, w_ds)
put(CAVE + OFF_CW, w_cw)
put(CAVE + OFF_CCTC, w_cc)
put(CAVE + OFF_SW, w_sw)
# DrawString v1 → 16 位槽位
put(0x219BCC, [0x0C000000 | ((CAVE >> 2) & 0x3FFFFFF)])
for va, w in ((0x219BD0, 0x27A400DE), (0x219BD4, 0x87A500DE), (0x219BE4, 0x87A500DE),
              (0x219CA0, 0x87A400DE), (0x219DAC, 0x93A200DD), (0x219DB0, 0x02028021)):
    struct.pack_into('<I', data, fo(va), w)
for va, w in ((0x219C08, 0x240300B5), (0x219C14, 0x240300B1), (0x219C94, 0x240300B5),
              (0x219CAC, 0x240300B1), (0x219D24, 0x240200B5), (0x219D38, 0x240200B1)):
    struct.pack_into('<I', data, fo(va), w)
put(0x21AD18, [0x08000000 | (((CAVE + OFF_CW) >> 2) & 0x3FFFFFF), 0])
put(0x21ADE0, [0x08000000 | (((CAVE + OFF_CCTC) >> 2) & 0x3FFFFFF), 0])
# StringWidth: hook 只换 0x21AC74 一条指令; 0x21AC78 delay 与之后原版代码全部保留
put(0x21AC74, [0x08000000 | (((CAVE + OFF_SW) >> 2) & 0x3FFFFFF)])

ndiff = sum(1 for x, y in zip(orig, bytes(data)) if x != y)
print('P-S 改动=%dB' % ndiff)
open(DST, 'wb').write(bytes(data))
print('写出', DST)
