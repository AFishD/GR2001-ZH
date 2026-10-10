# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/patch_db2c.py (逐字复制 (Stage2 参数化二分 + MIPS Asm 套件; build_PS_v5 依赖其文本))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""patch_db2c.py — 参数化二分版 Stage2 ELF
用法: patch_db2c.py <out.elf> <cw:0/1> <cctc:0/1> <sw:0/1>
ds16+槽位+立即数始终启用; cw/cctc/sw 三个 cave 钩子按参数开关 (0=保持原版代码)
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys

sys.path.insert(0, os.path.join(REPO_ROOT, 'work', 'tmp', 'slus_scan'))
import importlib.util
spec = importlib.util.spec_from_file_location('pdb2b', os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'patch_db2b_elf.py'))
# 不能直接 import (会执行 main); 复制关键构件:
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
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
    def _r(self, op, rs, rt, rd, sa, fn): self.i((op<<26)|(g(rs)<<21)|(g(rt)<<16)|(g(rd)<<11)|(sa<<6)|fn)
    def r2(self, rs, rt, rd, fn): self._r(0, rs, rt, rd, 0, fn)
    def sll(self, rd, rt, sa): self._r(0,0,rt,rd,sa,0x00)
    def srl(self, rd, rt, sa): self._r(0,0,rt,rd,sa,0x02)
    def jr(self, rs): self._r(0,rs,0,0,0,0x08)
    def addu(self, rd, rs, rt): self.r2(rs, rt, rd, 0x21)
    def sltu(self, rd, rs, rt): self.r2(rs, rt, rd, 0x2B)
    def slt(self, rd, rs, rt): self.r2(rs, rt, rd, 0x2A)
    def subu(self, rd, rs, rt): self.r2(rs, rt, rd, 0x23)
    def or_(self, rd, rs, rt): self.r2(rs, rt, rd, 0x25)
    def mult3(self, rd, rs, rt): self.r2(rs, rt, rd, 0x18)
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

def lead_checks(a, creq, cval, done):
    a.sltiu(creq, cval, 0xA1); a.bne(creq, 'zero', done); a.i(0)
    a.sltiu(creq, cval, 0xFF); a.beq(creq, 'zero', done); a.i(0)
    for rc in (0xAE, 0xB1, 0xB5, 0xE7, 0xF1):
        a.addiu('t1', 'zero', rc); a.beq(cval, 't1', done)
    a.i(0)

def build_ds16(a):
    a.andi('a1', 'a1', 0xFF)
    a.sh('a1', 0, 'a0')
    a.addiu('v0', 'zero', 1)
    lead_checks(a, 't1', 'a1', 'done')
    a.addiu('t8', 's7', -1 & 0xFFFF)
    a.slt('t8', 's0', 't8')
    a.beq('t8', 'zero', 'done'); a.i(0)
    a.addu('t7', 's6', 's0')
    a.lbu('t3', 1, 't7')
    a.sltiu('t1', 't3', 0xA1); a.bne('t1', 'zero', 'done'); a.i(0)
    a.sltiu('t1', 't3', 0xFF); a.beq('t1', 'zero', 'done'); a.i(0)
    a.sll('t4', 'a1', 8)
    a.or_('t4', 't4', 't3')
    a.sh('t4', 0, 'a0')
    a.addiu('v0', 'zero', 2)
    a.label('done')
    a.sb('v0', -1, 'a0')
    a.jr('ra'); a.i(0)

def build_cw(a):
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
    a.beq('v0', 'zero', 'idx0'); a.i(0)
    a.beq('zero', 'zero', 'have'); a.i(0)
    a.label('idx0')
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
    a._i(0x37, 'sp', 'ra', 0)
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

SW_EPI = 0x0021ACA4
def build_sw(a, charwidth):
    a.addiu('s5', 'zero', 0)
    a.label('loop')
    a.slt('v1', 's4', 's0')
    a.beq('v1', 'zero', 'done'); a.i(0)
    a.addu('a3', 's2', 's4')
    a.lbu('t0', 0, 'a3')
    lead_checks(a, 'v0', 't0', 'single')
    a.addiu('t8', 's0', -1 & 0xFFFF)
    a.slt('t8', 's4', 't8')
    a.beq('t8', 'zero', 'single'); a.i(0)
    a.lbu('t1', 1, 'a3')
    a.sltiu('v0', 't1', 0xA1); a.bne('v0', 'zero', 'single'); a.i(0)
    a.sll('a1', 't0', 8)
    a.or_('a1', 'a1', 't1')
    a.addiu('s6', 'zero', 2)
    a.beq('zero', 'zero', 'callw'); a.i(0)
    a.label('single')
    a.addu('a1', 't0', 'zero')
    a.addiu('s6', 'zero', 1)
    a.label('callw')
    a.jal(charwidth)
    a.addu('a0', 's3', 'zero')
    a.addu('s1', 's1', 'v0')
    a.addiu('s5', 's5', 1)
    a.addu('s4', 's4', 's6')
    a.beq('zero', 'zero', 'loop'); a.i(0)
    a.label('done')
    a.lw('v0', 0x18, 's3')
    a.addiu('v1', 's5', -1)
    a.mult3('v0', 'v1', 'v0')
    a.addu('s1', 's1', 'v0')
    a.addu('v0', 's1', 'zero')
    a.addu('a1', 's5', 'zero')
    a.j(SW_EPI); a.i(0)

CAVE = 0x26BEA0
OFF_DS, OFF_CW, OFF_CCTC, OFF_SW = 0x000, 0x09C, 0x184, 0x1E8
RESUME_CCTC = 0x21AE20

def main():
    dst = sys.argv[1]
    hook_cw, hook_cctc, hook_sw = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    data = bytearray(open(os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13'), 'rb').read())
    orig = bytes(data)
    fo = lambda va: SEC_OFF + va - SEC_ADDR
    def rd(va): return struct.unpack_from('<I', data, fo(va))[0]

    assert rd(0x219BCC) == 0x0C102FF2 and rd(0x219BD0) == 0x27A400DF
    a_ds = Asm(); build_ds16(a_ds); w_ds = a_ds.resolve(CAVE + OFF_DS)
    a_sw = Asm(); build_sw(a_sw, 0x0021AD10); w_sw = a_sw.resolve(CAVE + OFF_SW)
    a_cw = Asm(); build_cw(a_cw); w_cw = a_cw.resolve(CAVE + OFF_CW)
    a_cc = Asm(); build_cctc(a_cc, RESUME_CCTC); w_cc = a_cc.resolve(CAVE + OFF_CCTC)

    def put(va, words):
        for k, w in enumerate(words):
            struct.pack_into('<I', data, fo(va) + 4*k, w)

    put(CAVE + OFF_DS, w_ds)
    if hook_sw:
        put(CAVE + OFF_SW, w_sw)
    if hook_cw:
        put(CAVE + OFF_CW, w_cw)
    if hook_cctc:
        put(CAVE + OFF_CCTC, w_cc)

    # DrawString v1 槽位 (总是)
    put(0x219BCC, [0x0C000000 | (((CAVE+OFF_DS)>>2) & 0x3FFFFFF)])
    for va, w in ((0x219BD0, 0x27A400DE), (0x219BD4, 0x87A500DE), (0x219BE4, 0x87A500DE),
                  (0x219CA0, 0x87A400DE), (0x219DAC, 0x93A200DD), (0x219DB0, 0x02028021)):
        struct.pack_into('<I', data, fo(va), w)
    # 立即数 (总是)
    for va, w in ((0x219C08, 0x240300B5), (0x219C14, 0x240300B1), (0x219C94, 0x240300B5),
                  (0x219CAC, 0x240300B1), (0x219D24, 0x240200B5), (0x219D38, 0x240200B1)):
        struct.pack_into('<I', data, fo(va), w)
    # 钩子
    if hook_cw:
        put(0x21AD18, [0x08000000 | (((CAVE+OFF_CW)>>2) & 0x3FFFFFF), 0])
    if hook_cctc:
        put(0x21ADE0, [0x08000000 | (((CAVE+OFF_CCTC)>>2) & 0x3FFFFFF), 0])
    if hook_sw:
        put(0x21AC74, [0x08000000 | (((CAVE+OFF_SW)>>2) & 0x3FFFFFF)])
        struct.pack_into('<I', data, fo(0x21AC78), 0x02003021)
        for va in range(0x21AC7C, 0x21ACA4, 4):
            struct.pack_into('<I', data, fo(va), 0)

    ndiff = sum(1 for x, y in zip(orig, bytes(data)) if x != y)
    print('%s cw=%d cctc=%d sw=%d 改动=%dB' % (dst, hook_cw, hook_cctc, hook_sw, ndiff))
    open(dst, 'wb').write(bytes(data))

if __name__ == '__main__':
    main()
