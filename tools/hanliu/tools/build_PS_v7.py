# [hanliu 收编] 原件: C:/gr_build/tmp/zh8b/build_PS_v7.py (逐字复制)。原件保留于原处未动。
# -*- coding: utf-8 -*-
"""build_PS_v7.py — ZH8b ELF: v6 + 直 UV 路径宽度补偿 → SLUS_P_V7.elf

唯一改动 (build_cw 直 UV 分支): 返回宽 = CELL_W (12), 不再乘 RSFont+0x1C (样式 scaleX)。

机制 (反汇编实证, tmp\zh8b\dis_va.py):
  - 原版 RSFont::CharWidth (0x21AD10) 记录路径 = fptosi(adv_byte × float[RSFont+0x1C]);
    RSFontMgr 8 样式按值存, +0x1C = 样式 scaleX (fontmgr_probe2: large 系样式含 1.0/1.64,
    huge 系 0.8/1.63)。原版 large-face 图集字形是「按 1.64 预拉宽」绘制的, 故记录路径 1:1。
  - v6 直 UV 路径照搬 ×scaleX ⇒ quad 宽 = fptosi(12×1.64)=19px, UV 带仅 12 texel
    ⇒ large 样式 widget (Controller 左列等) 横向拉伸 ~1.64×; default(scaleX=1.0) 面 1:1 正常。
  - v7: 直 UV 分支 v0=CELL_W 直接返回 ⇒ quad 宽 12px = 带 12 texel, 任意样式 scaleX 下恒 1:1;
    huge(0.8) 面同时修复 (v6 为 fptosi(9.6)=9px 的 0.75 压扁)。default 面输出与 v6 逐位一致。
  - cctc/ds16/sw 三 cave 与全部挂点 = v6 逐字节同布局 (cave 用量 -5 条指令)。

在 build_PS_v6 (SLUS_P_V6.elf) 基础上保持:
  1. ds16/sw 的 lead 上界 0xAE (13 lead: A1..AD)。
  2. cw/cctc 的对分支 mSize 自适应: idx=224+slot < mSize → 记录路径; ≥ → 直接 UV (41列×12×15, Y0=128)。
  3. 槽位改造 (lhu)/六处图标码立即数与 v5/v6 完全一致。
  cave 0x26BEA0..0x26C18F (748B): ds@0x000 cw@0x070 cctc@0x180 sw@0x25C。
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, os, sys

SRC = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
DST = os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_V7.elf')
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
fo = lambda va: SEC_OFF + va - SEC_ADDR
data = bytearray(open(SRC, 'rb').read())
orig = bytes(data)
def rd(va): return struct.unpack_from('<I', data, fo(va))[0]
assert rd(0x219BCC) == 0x0C102FF2 and rd(0x21AC74) == 0x0C086B44

# --- Asm (patch_db2c.py 同款, 补 div/mflo) ---
R = {'zero':0,'at':1,'v0':2,'v1':3,'a0':4,'a1':5,'a2':6,'a3':7,
     't0':8,'t1':9,'t2':10,'t3':11,'t4':12,'t5':13,'t6':14,'t7':15,
     's0':16,'s1':17,'s2':18,'s3':19,'s4':20,'s5':21,'s6':22,'s7':23,
     't8':24,'t9':25,'k0':26,'k1':27,'gp':28,'sp':29,'fp':30,'ra':31}
def g(k): return R[k] if isinstance(k, str) else k

class Asm:
    def __init__(self):
        self.w = []; self.lbl = {}; self.fix = []
    def i(self, word): self.w.append(word & 0xFFFFFFFF); return len(self.w)-1
    def label(self, name): self.lbl[name] = len(self.w)
    def _r(self, op, rs, rt, rd_, sa, fn): self.i((op<<26)|(g(rs)<<21)|(g(rt)<<16)|(g(rd_)<<11)|(sa<<6)|fn)
    def r2(self, rs, rt, rd_, fn): self._r(0, rs, rt, rd_, 0, fn)
    def sll(self, rd_, rt, sa): self._r(0,0,rt,rd_,sa,0x00)
    def srl(self, rd_, rt, sa): self._r(0,0,rt,rd_,sa,0x02)
    def jr(self, rs): self._r(0,rs,0,0,0,0x08)
    def addu(self, rd_, rs, rt): self.r2(rs, rt, rd_, 0x21)
    def sltu(self, rd_, rs, rt): self.r2(rs, rt, rd_, 0x2B)
    def slt(self, rd_, rs, rt): self.r2(rs, rt, rd_, 0x2A)
    def subu(self, rd_, rs, rt): self.r2(rs, rt, rd_, 0x23)
    def or_(self, rd_, rs, rt): self.r2(rs, rt, rd_, 0x25)
    def mult3(self, rd_, rs, rt): self.r2(rs, rt, rd_, 0x18)
    def div(self, rs, rt): self._r(0, rs, rt, 0, 0, 0x1A)
    def mflo(self, rd_): self._r(0, 0, 0, rd_, 0, 0x12)
    def b(self, op, rs, rt, target):
        self.fix.append((len(self.w), op, g(rs), g(rt), target)); self.i(0)
    def beq(self, rs, rt, t): self.b(0x04, rs, rt, t)
    def bne(self, rs, rt, t): self.b(0x05, rs, rt, t)
    def _i(self, op, rs, rt, imm): self.i((op<<26)|(g(rs)<<21)|(g(rt)<<16)|(imm & 0xFFFF))
    def addiu(self, rt, rs, imm): self._i(0x09, rs, rt, imm)
    def sltiu(self, rt, rs, imm): self._i(0x0B, rs, rt, imm)
    def andi(self, rt, rs, imm): self._i(0x0C, rs, rt, imm)
    def lw(self, rt, off, base): self._i(0x23, base, rt, off)
    def lbu(self, rt, off, base): self._i(0x24, base, rt, off)
    def lb(self, rt, off, base): self._i(0x20, base, rt, off)
    def sh(self, rt, off, base): self._i(0x29, base, rt, off)
    def sb(self, rt, off, base): self._i(0x28, base, rt, off)
    def lwc1(self, ft, off, base): self._i(0x31, base, ft, off)
    def swc1(self, ft, off, base): self._i(0x39, base, ft, off)
    def mtc1(self, rt, fs): self.i((0x11<<26)|(4<<21)|(g(rt)<<16)|(fs<<11))
    def cvt_s_w(self, fd, fs): self.i((0x11<<26)|(0x14<<21)|(fs<<16)|(fd<<6)|0x20)
    def mul_s(self, fd, fs, ft): self.i((0x11<<26)|(0x10<<21)|(fs<<16)|(ft<<11)|(fd<<6)|0x02)
    def jal(self, addr): self.i(0x0C000000 | ((addr>>2) & 0x3FFFFFF))
    def j(self, addr): self.i(0x08000000 | ((addr>>2) & 0x3FFFFFF))
    def resolve(self, pc):
        for wi, op, rs, rt, t in self.fix:
            tt = self.lbl[t] if isinstance(t, str) else t
            d = tt - (wi + 1)
            assert -0x8000 <= d < 0x8000
            self.w[wi] = ((op<<26)|(rs<<21)|(rt<<16)|(d & 0xFFFF))
        return self.w

CAVE = 0x26BEA0
OFF_DS, OFF_CW, OFF_CCTC, OFF_SW = 0x000, 0x070, 0x180, 0x25C
LEAD_HI = 0xAE          # lead ∈ [0xA1, 0xAE)
NCOL, CELL_W, CELL_H, Y0 = 41, 12, 15, 128
U0R, V0R = 0, Y0        # 记录坐标系 u0 = 0+12c, v0 = Y0+CELL_H*r (ZH8 布局: x=20+12c, y=128+15r)

def build_ds16(a):
    # 入口: a1 = lb 符号扩展的字节, a0 = &slot(sp+0xDE); s6=str s0=i s7=len (v5 同款, 上界改 0xAE)
    a.andi('a1', 'a1', 0xFF)
    a.sh('a1', 0, 'a0')
    a.addiu('v0', 'zero', 1)
    a.sltiu('t1', 'a1', 0xA1)
    a.bne('t1', 'zero', 'done'); a.i(0)
    a.sltiu('t1', 'a1', LEAD_HI)          # ≥ 0xAE → 单字节 (13-lead)
    a.beq('t1', 'zero', 'done'); a.i(0)
    a.addiu('t8', 's7', -1 & 0xFFFF)
    a.slt('t8', 's0', 't8')
    a.beq('t8', 'zero', 'done'); a.i(0)
    a.addu('t7', 's6', 's0')
    a.lbu('t3', 1, 't7')
    a.sltiu('t1', 't3', 0xA1)
    a.bne('t1', 'zero', 'done'); a.i(0)
    a.sltiu('t1', 't3', 0xFF)
    a.beq('t1', 'zero', 'done'); a.i(0)
    a.sll('t4', 'a1', 8)
    a.or_('t4', 't4', 't3')
    a.sh('t4', 0, 'a0')
    a.addiu('v0', 'zero', 2)
    a.label('done')
    a.sb('v0', -1, 'a0')
    a.jr('ra'); a.i(0)

def build_cw(a):
    # CharWidth: a0=this a1=char16(lhu 零扩展)
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
    a.beq('zero', 'zero', 'bounds'); a.lw('a2', 0x28, 'a0')
    a.label('ext')
    a.andi('t1', 't0', 0xFF)              # lead
    a.addiu('t1', 't1', -0xA1 & 0xFFFF)
    a.andi('t2', 'a1', 0xFF)              # trail
    a.addiu('t2', 't2', -0xA1 & 0xFFFF)
    a.addiu('t6', 'zero', 94)
    a.mult3('t0', 't1', 't6')
    a.addu('t0', 't0', 't2')              # slot
    a.addiu('t0', 't0', 224)              # idx = 224+slot
    a.lw('a2', 0x28, 'a0')                # ★ext 路径必须自取 FD (ASCII 路径的 a2 不经过此处)
    a.lw('v1', 0x44, 'a2')                # mSize
    a.sltu('v0', 't0', 'v1')
    a.bne('v0', 'zero', 'have'); a.addiu('v0', 'zero', CELL_W)   # 直接UV宽 = 12 (延迟槽预载)
    # --- 直接 UV 路径 (v7): 宽恒 = CELL_W, 不乘 RSFont+0x1C 样式 scaleX ---
    # 原版记录路径乘 scaleX 是因为原版图集字形按 scaleX 预拉宽; 直 UV 带 12 texel 恒 1:1。
    a.beq('zero', 'zero', 'epi'); a.i(0)
    a.label('have')                       # 记录路径 (idx < mSize, 已保证不越界)
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
    a.label('bounds')                     # ASCII 记录路径 (需 clamp)
    a.lw('v1', 0x44, 'a2')
    a.sltu('v0', 't0', 'v1')
    a.bne('v0', 'zero', 'have'); a.i(0)
    a.addiu('t0', 'zero', 0)
    a.beq('zero', 'zero', 'have'); a.i(0)
    a.label('ret_space')
    a.lw('v0', 0x14, 'a0')
    a.beq('zero', 'zero', 'epi'); a.i(0)
    a.label('ret20')
    a.addiu('v0', 'zero', 0x14)
    a.label('epi')
    a._i(0x37, 'sp', 'ra', 0)             # ld ra,0(sp)
    a.jr('ra'); a.addiu('sp', 'sp', 0x10)

def build_cctc(a, resume):
    # a0=this a1=char16 a2/a3/t0/t1 = 4 个 float 输出指针 (原版 0x21AE20 消费契约)
    a.lw('t2', 0x28, 'a0')
    a.andi('v1', 'a1', 0xFF)
    a.srl('t4', 'a1', 8)
    a.bne('t4', 'zero', 'ext'); a.i(0)
    a.lb('a1', 0x20, 't2')
    a.subu('v1', 'v1', 'a1')
    a.andi('a1', 'v1', 0xFF)
    a.beq('zero', 'zero', 'bounds'); a.i(0)
    a.label('ext')
    a.andi('t4', 't4', 0xFF)
    a.addiu('t4', 't4', -0xA1 & 0xFFFF)
    a.andi('t5', 'v1', 0xFF)
    a.addiu('t5', 't5', -0xA1 & 0xFFFF)
    a.addiu('t6', 'zero', 94)
    a.mult3('t4', 't4', 't6')
    a.addu('t4', 't4', 't5')              # slot
    a.addiu('a1', 't4', 224)              # idx
    a.label('bounds')
    a.lw('v1', 0x44, 't2')                # mSize
    a.sltu('v0', 'a1', 'v1')
    a.bne('v0', 'zero', 'ok'); a.i(0)
    # --- 直接 UV: slot = a1-224 ---
    a.addiu('t4', 'a1', -224 & 0xFFFF)    # slot
    a.addiu('t6', 'zero', NCOL)
    a.div('t4', 't6')                     # LO = slot/41
    a.mflo('t5')                          # row
    a.mult3('t6', 't5', 't6')             # row*41
    a.mflo('t6')
    a.subu('t4', 't4', 't6')              # col
    a.addiu('t7', 'zero', CELL_W)
    a.mult3('t6', 't4', 't7')             # 12*col
    a.mflo('t6')
    a.addiu('a1', 't6', U0R)              # u0 = 0+12c
    a.addiu('t4', 't6', U0R + CELL_W)     # u1 = u0+12
    a.addiu('t7', 'zero', CELL_H)
    a.mult3('t6', 't5', 't7')             # 15*row
    a.mflo('t6')
    a.addiu('t5', 't6', V0R)              # v0
    a.addiu('t6', 't6', V0R + CELL_H)     # v1
    a.mtc1('a1', 0); a.cvt_s_w(0, 0); a.swc1(0, 0, 'a2')
    a.mtc1('t5', 0); a.cvt_s_w(0, 0); a.swc1(0, 0, 'a3')
    a.mtc1('t4', 0); a.cvt_s_w(0, 0); a.swc1(0, 0, 't0')
    a.mtc1('t6', 0); a.cvt_s_w(0, 0)
    a.jr('ra')
    a.swc1(0, 0, 't1')                    # 延迟槽 (原版 0x21AF20 同款)
    a.label('ok')
    a.lw('t2', 0x38, 't2')
    a.j(resume); a.i(0)

def build_sw(a, charwidth):
    # StringWidth hook (v5 同款, 上界改 0xAE)
    ORIG = 0x0021AC7C
    LOOP = 0x0021AC84
    a.andi('t0', 'a1', 0xFF)
    a.sltiu('t1', 't0', 0xA1)
    a.bne('t1', 'zero', 'orig'); a.i(0)
    a.sltiu('t1', 't0', LEAD_HI)
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
print('ds16=%d cw=%d cctc=%d sw=%d 指令 (预算 ds<=28 cw<=68 cctc<=55 sw<=30)'
      % (len(w_ds), len(w_cw), len(w_cc), len(w_sw)))
assert len(w_ds) * 4 <= OFF_CW - OFF_DS
assert len(w_cw) * 4 <= OFF_CCTC - OFF_CW
assert len(w_cc) * 4 <= OFF_SW - OFF_CCTC
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
diffs = [i for i in range(len(data)) if orig[i] != data[i]]
inside_cave = [i for i in diffs if fo(CAVE) <= i < fo(CAVE) + 0x2EC]
hook_sites = set()
for v in (0x219BCC, 0x219BD0, 0x219BD4, 0x219BE4, 0x219CA0, 0x219DAC,
          0x219DB0, 0x219C08, 0x219C14, 0x219C94, 0x219CAC, 0x219D24,
          0x219D38, 0x21AD18, 0x21AD1C, 0x21ADE0, 0x21ADE4, 0x21AC74):
    hook_sites.update(range(fo(v), fo(v) + 4))
bad = [i for i in diffs if not (fo(CAVE) <= i < fo(CAVE) + 0x2EC or i in hook_sites)]
assert not bad, '差异越界: %s' % [hex(i) for i in bad[:8]]
# 原值断言 (与 v5/v6 相同的挂点原值)
assert rd(0x21AE20) == 0x00051880
os.makedirs(os.path.dirname(DST), exist_ok=True)
open(DST, 'wb').write(bytes(data))
print('P-V7 vs 原版 %dB 差异 (cave %d + 挂点 %d); 写出 %s'
      % (ndiff, len(inside_cave), len(diffs) - len(inside_cave), DST))

# --- v6 vs v7 差异断言: 应仅在 cw cave 的直 UV 分支 (少 5 条指令) ---
v6 = open(os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_V6.elf'), 'rb').read()
vd = [i for i in range(len(data)) if v6[i] != data[i]]
cave_lo, cave_hi = fo(CAVE + OFF_CW), fo(CAVE + OFF_CCTC)
assert all(cave_lo <= i < cave_hi for i in vd), \
    'v6↔v7 差异越出 cw cave: %s' % [hex(fo(0) + i) for i in vd[:8]]
print('v6↔v7 差异 %dB, 全部位于 cw cave 直 UV 分支' % len(vd))
print('PASS')
