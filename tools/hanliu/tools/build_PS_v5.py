# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/build_PS_v5.py (逐字复制 (lead 标记制终版 -> SLUS_P_U, GR_ZH7 采用))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""build_PS_v5.py — P-U: P-T + ds16/sw lead 改标记制 (marker-lead)
设计动机: ds16 把任意 (lead,trail ∈[A1,FE]) 消费成对 → 与 zh6 单字节汉字串冲突
  (相邻两个单字节汉字必被并成一个垃圾对)。v5 规定: **仅 lead ∈ {0xA1,0xA2,0xA3}
  时构成 DBCS 对** (此三码位的字符 役/有/下 在字符串中一律以对形式编码);
  其余 0xA4-0xFE 一律单字节 (不再查保留码表 —— 保留码 >0xA3 自动走单字节)。
  0xA1 诅咒 (u0=0) 与记录表无关, 仍由 atlas 起点控制。
改动: cave ds16 与 sw 的 lead 检查段 (比 v4 更短); cw/cctc/槽位/立即数与 P-T 相同。
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct

SRC = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
DST = os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_U.elf')
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
fo = lambda va: SEC_OFF + va - SEC_ADDR
data = bytearray(open(SRC, 'rb').read())
orig = bytes(data)
def rd(va): return struct.unpack_from('<I', data, fo(va))[0]
assert rd(0x219BCC) == 0x0C102FF2 and rd(0x21AC74) == 0x0C086B44

src = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'patch_db2c.py'), encoding='utf-8').read()
head = src.split('CAVE = 0x26BEA0')[0]
ns = {}
exec(head, ns)
Asm = ns['Asm']; R = ns['R']

CAVE = 0x26BEA0
OFF_DS, OFF_CW, OFF_CCTC, OFF_SW = 0x000, 0x09C, 0x184, 0x1E8

def build_ds16(a):
    # 入口: a1 = lb 符号扩展的字节, a0 = &slot(sp+0xDE); s6=str s0=i s7=len
    a.andi('a1', 'a1', 0xFF)
    a.sh('a1', 0, 'a0')                      # 先存单字节 (低半字)
    a.addiu('v0', 'zero', 1)
    a.sltiu('t1', 'a1', 0xA1)                # lead < A1 → 单
    a.bne('t1', 'zero', 'done'); a.i(0)
    a.sltiu('t1', 'a1', 0xA4)                # lead ≥ A4 → 单 (标记制: 仅 A1-A3 成对)
    a.beq('t1', 'zero', 'done'); a.i(0)
    a.addiu('t8', 's7', -1 & 0xFFFF)
    a.slt('t8', 's0', 't8')                  # i < len-1
    a.beq('t8', 'zero', 'done'); a.i(0)
    a.addu('t7', 's6', 's0')
    a.lbu('t3', 1, 't7')                     # trail
    a.sltiu('t1', 't3', 0xA1)
    a.bne('t1', 'zero', 'done'); a.i(0)
    a.sltiu('t1', 't3', 0xFF)
    a.beq('t1', 'zero', 'done'); a.i(0)
    a.sll('t4', 'a1', 8)
    a.or_('t4', 't4', 't3')
    a.sh('t4', 0, 'a0')                      # char16 = (lead<<8)|trail
    a.addiu('v0', 'zero', 2)
    a.label('done')
    a.sb('v0', -1, 'a0')                     # 步长槽 [sp+0xDD]
    a.jr('ra'); a.i(0)

def build_cw(a):
    # CharWidth: a0=this a1=char(lhu 零扩展); 高字节≠0 → DBCS idx; 否则单字节原语义
    a.srl('t0', 'a1', 8)
    a.bne('t0', 'zero', 'ext'); a.i(0)
    a.andi('t3', 'a1', 0xFF)
    a.addiu('t1', 'zero', 0x20)
    a.beq('t3', 't1', 'ret_space'); a.i(0)
    a.addiu('t1', 'zero', 0xB5)
    a.beq('t3', 't1', 'ret20'); a.i(0)
    a.addiu('t1', 'zero', 0xB1)
    a.beq('t3', 't1', 'ret20'); a.i(0)
    a.lw('a2', 0x28, 'a0')
    a.lb('v1', 0x20, 'a2')
    a.subu('t0', 't3', 'v1')
    a.andi('t0', 't0', 0xFF)
    a.beq('zero', 'zero', 'bounds'); a.i(0)
    a.label('ext')
    a.addiu('t0', 't0', -0xA1 & 0xFFFF)
    a.andi('t1', 'a1', 0xFF)
    a.addiu('t1', 't1', -0xA1 & 0xFFFF)
    a.addiu('t2', 'zero', 94)
    a.mult3('t0', 't0', 't2')
    a.addu('t0', 't0', 't1')
    a.addiu('t0', 't0', 224)
    a.lw('a2', 0x28, 'a0')
    a.label('bounds')
    a.lw('v1', 0x44, 'a2')
    a.sltu('v0', 't0', 'v1')
    a.bne('v0', 'zero', 'have'); a.i(0)
    a.addiu('t0', 'zero', 0)
    a.label('have')
    a.lw('a2', 0x38, 'a2')
    a.sll('v0', 't0', 2)
    a.addu('v0', 'v0', 't0')
    a.sll('v0', 'v0', 1)
    a.addu('v0', 'v0', 'a2')
    a.lbu('v0', 1, 'v0')
    a.mtc1('v0', 0)
    a.cvt_s_w(0, 0)
    a.lwc1(1, 0x1C, 'a0')
    a.mul_s(12, 1, 0)
    a.jal(0x00118EE0); a.i(0)
    a.beq('zero', 'zero', 'epi'); a.i(0)
    a.label('ret_space')
    a.lw('v0', 0x14, 'a0')
    a.beq('zero', 'zero', 'epi'); a.i(0)
    a.label('ret20')
    a.addiu('v0', 'zero', 0x14)
    a.label('epi')
    a._i(0x37, 'sp', 'ra', 0)                # ld ra,0(sp)
    a.jr('ra'); a.addiu('sp', 'sp', 0x10)

def build_cctc(a, resume):
    a.lw('t2', 0x28, 'a0')
    a.andi('v1', 'a1', 0xFF)
    a.srl('t4', 'a1', 8)
    a.bne('t4', 'zero', 'ext'); a.i(0)
    a.lb('a1', 0x20, 't2')
    a.subu('v1', 'v1', 'a1')
    a.andi('a1', 'v1', 0xFF)
    a.beq('zero', 'zero', 'bounds'); a.i(0)
    a.label('ext')
    a.addiu('t4', 't4', -0xA1 & 0xFFFF)
    a.andi('t5', 'a1', 0xFF)
    a.addiu('t5', 't5', -0xA1 & 0xFFFF)
    a.addiu('t6', 'zero', 94)
    a.mult3('t4', 't4', 't6')
    a.addu('t4', 't4', 't5')
    a.addiu('a1', 't4', 224)
    a.label('bounds')
    a.lw('v1', 0x44, 't2')
    a.sltu('v0', 'a1', 'v1')
    a.bne('v0', 'zero', 'ok'); a.i(0)
    a.addiu('a1', 'zero', 0)
    a.label('ok')
    a.lw('t2', 0x38, 't2')
    a.j(resume); a.i(0)

def build_sw(a, charwidth):
    # StringWidth hook: a1=char(lb) v0=str+i s0=len s4=i s3=font
    ORIG = 0x0021AC7C
    LOOP = 0x0021AC84
    a.andi('t0', 'a1', 0xFF)
    a.sltiu('t1', 't0', 0xA1)
    a.bne('t1', 'zero', 'orig'); a.i(0)
    a.sltiu('t1', 't0', 0xA4)                # 标记制: 仅 A1-A3
    a.beq('t1', 'zero', 'orig'); a.i(0)
    a.addiu('t8', 's0', -1 & 0xFFFF)
    a.slt('t8', 's4', 't8')
    a.beq('t8', 'zero', 'orig'); a.i(0)
    a.lbu('t3', 1, 'v0')
    a.sltiu('t1', 't3', 0xA1)
    a.bne('t1', 'zero', 'orig'); a.i(0)
    a.sltiu('t1', 't3', 0xFF)
    a.beq('t1', 'zero', 'orig'); a.i(0)
    a.sll('a1', 't0', 8)
    a.or_('a1', 'a1', 't3')
    a.jal(charwidth)
    a.i(0)
    a.addu('s1', 's1', 'v0')
    a.addiu('s4', 's4', 2)
    a.j(LOOP); a.i(0)
    a.label('orig')
    a.jal(charwidth)
    a.i(0)
    a.j(ORIG); a.i(0)

a_ds = Asm(); build_ds16(a_ds); w_ds = a_ds.resolve(CAVE + OFF_DS)
a_cw = Asm(); build_cw(a_cw); w_cw = a_cw.resolve(CAVE + OFF_CW)
a_cc = Asm(); build_cctc(a_cc, 0x21AE20); w_cc = a_cc.resolve(CAVE + OFF_CCTC)
a_sw = Asm(); build_sw(a_sw, 0x0021AD10); w_sw = a_sw.resolve(CAVE + OFF_SW)
print('ds16=%d cw=%d cctc=%d sw=%d 指令' % (len(w_ds), len(w_cw), len(w_cc), len(w_sw)))
assert len(w_ds) * 4 <= OFF_CW - OFF_DS
assert len(w_cw) * 4 <= OFF_SW - OFF_CW
assert CAVE + OFF_SW + len(w_sw) * 4 <= CAVE + 0x2EC

def put(va, words):
    for k, w in enumerate(words):
        struct.pack_into('<I', data, fo(va) + 4 * k, w)
put(CAVE + OFF_DS, w_ds)
put(CAVE + OFF_CW, w_cw)
put(CAVE + OFF_CCTC, w_cc)
put(CAVE + OFF_SW, w_sw)
put(0x219BCC, [0x0C000000 | ((CAVE >> 2) & 0x3FFFFFF)])
for va, w in ((0x219BD0, 0x27A400DE), (0x219BD4, 0x97A500DE), (0x219BE4, 0x97A500DE),
              (0x219CA0, 0x97A400DE), (0x219DAC, 0x93A200DD), (0x219DB0, 0x02028021)):
    struct.pack_into('<I', data, fo(va), w)
for va, w in ((0x219C08, 0x240300B5), (0x219C14, 0x240300B1), (0x219C94, 0x240300B5),
              (0x219CAC, 0x240300B1), (0x219D24, 0x240200B5), (0x219D38, 0x240200B1)):
    struct.pack_into('<I', data, fo(va), w)
put(0x21AD18, [0x08000000 | (((CAVE + OFF_CW) >> 2) & 0x3FFFFFF), 0])
put(0x21ADE0, [0x08000000 | (((CAVE + OFF_CCTC) >> 2) & 0x3FFFFFF), 0])
put(0x21AC74, [0x08000000 | (((CAVE + OFF_SW) >> 2) & 0x3FFFFFF)])

ndiff = sum(1 for x, y in zip(orig, bytes(data)) if x != y)
pt = open(os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'SLUS_P_T.elf'), 'rb').read()
dif = [i for i in range(len(data)) if pt[i] != data[i]]
print('P-U vs 原版 %dB; vs P-T 差异 %d B @%s' % (ndiff, len(dif), [hex(x) for x in dif]))
assert all(fo(CAVE) <= i < fo(CAVE) + 0x2EC for i in dif), '差异应仅在 cave'
open(DST, 'wb').write(bytes(data))
print('写出', DST)
