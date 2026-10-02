# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/patch_db2b_elf.py (逐字复制 (Stage2 v2 存档))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""patch_db2b_elf.py — Stage2 DBCS ELF 补丁 修订版 v2 (修复 v1 三处缺陷, 实测毒源)

v1 (patch_db2_elf.py) 三处缺陷与修复:
  F1 【boot 挂死根因, 探针 E 实证】sw cave 自建 -0x30 帧且直接 ld ra/addiu sp,sp,0x30/jr ra 返回,
     未撤销原版 StringWidth 序言 (0x21AC00: addiu sp,sp,-0x60; sd ra,0x50(sp); sq s0-s4×4) 的
     0x60 栈帧 → 每次 StringWidth 调用泄漏 0x30B 且调用方以错误 sp 运行 → boot f2817
     (LOAD_NEW_2.RSB 预处理, 首次字符串测宽) 引擎假活挂死, cdvd 静默于 LBA≈799173。
     修复: cave 不建帧, 只用原函数已占用的 s0-s4 + 已入帧保护的 s5/s6/s7 + t/v/a 寄存器;
     结尾 j 0x21ACA4 原版 epilogue (ld ra,0x50(sp); lq s0-s7; addiu sp,sp,0x60; jr ra) → 栈严格平衡。
     kerning ((chars-1)*mKerningOffset) 一并移入 cave。
  F2 cctc cave 单字节路径缺 andi v1,a1,0xFF (原 0x21ADE4 被 j 覆盖, v1 未补) → ASCII 索引不定;
     且跳回 0x21AE20 前缺 lw t2,0x38(t2) (FontDefinition→mKerningData 解引用) → UV 基址错。
     修复: 入口补 andi; resume 前补 lw t2,0x38(t2)。
  F3 16 位化后字符经 lh 读出为 0x00B1/0x00B5 (正数), DrawString v1 内 6 处按 -0x4F/-0x4B
     有符号立即数比较图标码 (±µ 按钮 glyph) 全部失配 → 图标退化为字形。
     修复: 6 处 addiu 立即数 -0x4B→0xB5 / -0x4F→0xB1 (0x219C08/0x219C14/0x219C94/0x219CAC/
     0x219D24/0x219D38)。

ABI: idx = 224 + (lead-0xA1)*94 + (trail-0xA1), lead/trail ∈ [0xA1,0xFE], lead 排除保留 5 码;
     字符槽 [sp+0xDE] 半字 = (lead<<8)|trail, 步长槽 [sp+0xDD]; large/huge 的 DBCS idx≥96 越界回退 0。
4 cave @ 0x26BEA0..0x26C18B (748B 死代码区 FindPropertyForModelID+FindPropertyForID, 零引用):
  ds16 @ +0x000 (jal 自 0x219BCC)   cw   @ +0x0A4 (j 自 0x21AD18)
  cctc @ +0x184 (j 自 0x21ADE0, 复活 0x21AE20)   sw @ +0x1E0 (j 自 0x21AC74, 经 0x21ACA4 epilogue 返回)
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys

sys.path.insert(0, os.path.join(REPO_ROOT, 'work', 'tmp', 'slus_scan'))
import dis4

SRC = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
DST = os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'SLUS_db2b.elf')
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
            assert -0x8000 <= d < 0x8000, (wi, t, d)
            self.w[wi] = ((op<<26)|(rs<<21)|(rt<<16)|(d & 0xFFFF))
        return self.w

def lead_checks(a, creq, cval, done):
    """lead∈[0xA1,0xFE] 且 ∉{0xAE,0xB1,0xB5,0xE7,0xF1}; 破坏 creq/t1"""
    a.sltiu(creq, cval, 0xA1); a.bne(creq, 'zero', done); a.i(0)
    a.sltiu(creq, cval, 0xFF); a.beq(creq, 'zero', done); a.i(0)
    for rc in (0xAE, 0xB1, 0xB5, 0xE7, 0xF1):
        a.addiu('t1', 'zero', rc); a.beq(cval, 't1', done)
    a.i(0)

# ---------- cave 1: ds16 (DrawString 取字符翻译) ----------
def build_ds16(a):
    """a0=dest(sp+0xDE), a1=c, a2=ptr → sh [a0]=char16, sb [a0-1]=step; 破坏 t1/t3/t4/t7/t8/v0"""
    a.andi('a1', 'a1', 0xFF)
    a.sh('a1', 0, 'a0')                    # 默认: 零扩展字节
    a.addiu('v0', 'zero', 1)
    lead_checks(a, 't1', 'a1', 'done')
    a.addiu('t8', 's7', -1 & 0xFFFF)       # len-1 (s7=strlen live)
    a.slt('t8', 's0', 't8')                # i < len-1 ?
    a.beq('t8', 'zero', 'done'); a.i(0)
    a.addu('t7', 's6', 's0')               # ptr = str+i
    a.lbu('t3', 1, 't7')                   # trail
    a.sltiu('t1', 't3', 0xA1); a.bne('t1', 'zero', 'done'); a.i(0)
    a.sltiu('t1', 't3', 0xFF); a.beq('t1', 'zero', 'done'); a.i(0)
    a.sll('t4', 'a1', 8)
    a.or_('t4', 't4', 't3')
    a.sh('t4', 0, 'a0')
    a.addiu('v0', 'zero', 2)
    a.label('done')
    a.sb('v0', -1, 'a0')
    a.jr('ra'); a.i(0)

# ---------- cave 2: cw (CharWidth 主体) ----------
def build_cw(a):
    """j 自 0x21AD18; 原 prologue 已 sd ra,0(sp), sp-=0x10; a0=font a1=char16 → v0=宽"""
    a.srl('t0', 'a1', 8)
    a.bne('t0', 'zero', 'ext'); a.i(0)
    a.andi('t3', 'a1', 0xFF)
    a.addiu('t1', 'zero', 0x20)
    a.beq('t3', 't1', 'ret_space'); a.i(0)
    a.addiu('t1', 'zero', 0xB5)
    a.beq('t3', 't1', 'ret20'); a.i(0)
    a.addiu('t1', 'zero', 0xB1)
    a.beq('t3', 't1', 'ret20'); a.i(0)
    a.lw('a2', 0x28, 'a0')                 # FD
    a.lb('v1', 0x20, 'a2')                 # mStartChar
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
    a.lw('v1', 0x44, 'a2')                 # mSize
    a.sltu('v0', 't0', 'v1')
    a.beq('v0', 'zero', 'idx0'); a.i(0)
    a.beq('zero', 'zero', 'have'); a.i(0)
    a.label('idx0')
    a.addiu('t0', 'zero', 0)
    a.label('have')
    a.lw('a2', 0x38, 'a2')                 # mKerningData
    a.sll('v0', 't0', 2)
    a.addu('v0', 'v0', 't0')
    a.sll('v0', 'v0', 1)
    a.addu('v0', 'v0', 'a2')
    a.lbu('v0', 1, 'v0')                   # 记录 byte1 = 宽
    a.mtc1('v0', 0)
    a.cvt_s_w(0, 0)
    a.lwc1(1, 0x1C, 'a0')                  # mScaleX
    a.mul_s(12, 1, 0)
    a.jal(0x00118EE0); a.i(0)              # fptosi(f12) → v0
    a.beq('zero', 'zero', 'epi'); a.i(0)
    a.label('ret_space')
    a.lw('v0', 0x14, 'a0')                 # mSpaceWidth
    a.beq('zero', 'zero', 'epi'); a.i(0)
    a.label('ret20')
    a.addiu('v0', 'zero', 0x14)
    a.label('epi')
    a._i(0x37, 'sp', 'ra', 0)              # ld ra,0(sp)
    a.jr('ra'); a.addiu('sp', 'sp', 0x10)

# ---------- cave 3: cctc (ComputeCharTextureCoords 索引前段) ----------
def build_cctc(a, resume):
    """j 自 0x21ADE0。出口: t2=KD, a1=idx, j resume。v2: 补 andi v1 与 lw t2,0x38"""
    a.lw('t2', 0x28, 'a0')                 # FD
    a.andi('v1', 'a1', 0xFF)               # ★F2a 单字节: v1 = char&0xFF (原 0x21ADE4)
    a.srl('t4', 'a1', 8)
    a.bne('t4', 'zero', 'ext'); a.i(0)
    a.lb('a1', 0x20, 't2')                 # mStartChar
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
    a.lw('t2', 0x38, 't2')                 # ★F2b t2 = mKerningData
    a.j(resume); a.i(0)

# ---------- cave 4: sw (StringWidth 主循环, 无栈帧版) ----------
SW_EPI = 0x0021ACA4   # 原版 epilogue: ld ra,0x50(sp); lq s0-s7; addiu sp,sp,0x60; jr ra

def build_sw(a, charwidth):
    """j 自 0x21AC74 (delay addu a2,s0,zero)。入口: s0=len s1=0 s2=str s3=font s4=0
       (原函数前奏已置)。只用 s0-s7/t/v/a, 不碰 sp/ra; 出口 v0=s1=总宽, j 原版 epilogue。"""
    a.addiu('s5', 'zero', 0)               # chars = 0 (s5 原为调用方值, 已入帧保护)
    a.label('loop')
    a.slt('v1', 's4', 's0')                # i < len
    a.beq('v1', 'zero', 'done'); a.i(0)
    a.addu('a3', 's2', 's4')
    a.lbu('t0', 0, 'a3')
    lead_checks(a, 'v0', 't0', 'single')
    a.addiu('t8', 's0', -1 & 0xFFFF)       # len-1
    a.slt('t8', 's4', 't8')
    a.beq('t8', 'zero', 'single'); a.i(0)  # 末字符 → 单字节
    a.lbu('t1', 1, 'a3')                   # trail (0xFF 允许)
    a.sltiu('v0', 't1', 0xA1); a.bne('v0', 'zero', 'single'); a.i(0)
    a.sll('a1', 't0', 8)
    a.or_('a1', 'a1', 't1')                # char16 直入 a1
    a.addiu('s6', 'zero', 2)
    a.beq('zero', 'zero', 'callw'); a.i(0)
    a.label('single')
    a.addu('a1', 't0', 'zero')
    a.addiu('s6', 'zero', 1)
    a.label('callw')
    a.jal(charwidth)                       # ra 被破坏无妨: 出口经 epilogue 从帧恢复
    a.addu('a0', 's3', 'zero')             # delay: a0=font
    a.addu('s1', 's1', 'v0')               # acc += 宽
    a.addiu('s5', 's5', 1)                 # chars++
    a.addu('s4', 's4', 's6')               # i += step
    a.beq('zero', 'zero', 'loop'); a.i(0)
    a.label('done')
    a.lw('v0', 0x18, 's3')                 # mKerningOffset
    a.addiu('v1', 's5', -1)
    a.mult3('v0', 'v1', 'v0')              # (chars-1)*kern
    a.addu('s1', 's1', 'v0')
    a.addu('v0', 's1', 'zero')             # v0 = 总宽
    a.addu('a1', 's5', 'zero')             # a1 = 字符数 (信息位)
    a.j(SW_EPI); a.i(0)                    # 原版 epilogue 全量恢复

CAVE = 0x26BEA0
OFF_DS, OFF_CW, OFF_CCTC, OFF_SW = 0x000, 0x09C, 0x184, 0x1E8
RESUME_CCTC = 0x21AE20

def main():
    data = bytearray(open(SRC, 'rb').read())
    orig = bytes(data)
    fo = lambda va: SEC_OFF + va - SEC_ADDR
    def rd(va): return struct.unpack_from('<I', data, fo(va))[0]

    # 原值断言 (补丁点)
    assert rd(0x219BCC) == 0x0C102FF2 and rd(0x219BD0) == 0x27A400DF
    assert rd(0x219BD4) == 0x83A500DF and rd(0x219BE4) == 0x83A500DF and rd(0x219CA0) == 0x83A400DF
    assert rd(0x219DAC) == 0 and rd(0x219DB0) == 0x26100001
    assert rd(0x21AD18) == 0x90820024 and rd(0x21AD1C) == 0x10400003
    assert rd(0x21ADE0) == 0x8C8A0028 and rd(0x21ADE4) == 0x30A300FF
    assert rd(0x21AC6C) == 0x02541021 and rd(0x21AC70) == 0x80450000 and rd(0x21AC74) == 0x0C086B44
    assert rd(0x21AE20) == 0x00051880
    # F3 图标码比较点原值
    for va, want in ((0x219C08, 0x2403FFB5), (0x219C14, 0x2403FFB1),
                     (0x219C94, 0x2403FFB5), (0x219CAC, 0x2403FFB1),
                     (0x219D24, 0x2402FFB5), (0x219D38, 0x2402FFB1)):
        assert rd(va) == want, (hex(va), hex(rd(va)))

    a_ds = Asm(); build_ds16(a_ds)
    a_cw = Asm(); build_cw(a_cw)
    a_cc = Asm(); build_cctc(a_cc, RESUME_CCTC)
    a_sw = Asm(); build_sw(a_sw, 0x0021AD10)
    w_ds = a_ds.resolve(CAVE + OFF_DS)
    w_cw = a_cw.resolve(CAVE + OFF_CW)
    w_cc = a_cc.resolve(CAVE + OFF_CCTC)
    w_sw = a_sw.resolve(CAVE + OFF_SW)
    for name, ws, off in (('ds16', w_ds, OFF_DS), ('cw', w_cw, OFF_CW),
                          ('cctc', w_cc, OFF_CCTC), ('sw', w_sw, OFF_SW)):
        assert CAVE + off + len(ws)*4 <= CAVE + 0x2EC, (name, len(ws))
        print('%s: %d 指令 @0x%X..0x%X' % (name, len(ws), CAVE+off, CAVE+off+len(ws)*4-1))

    def put(va, words):
        for k, w in enumerate(words):
            struct.pack_into('<I', data, fo(va) + 4*k, w)

    put(CAVE + OFF_DS, w_ds)
    put(CAVE + OFF_CW, w_cw)
    put(CAVE + OFF_CCTC, w_cc)
    put(CAVE + OFF_SW, w_sw)

    # DrawString v1 → 16 位槽位
    put(0x219BCC, [0x0C000000 | (((CAVE+OFF_DS)>>2) & 0x3FFFFFF)])
    struct.pack_into('<I', data, fo(0x219BD0), 0x27A400DE)   # addiu a0,sp,0xDE
    struct.pack_into('<I', data, fo(0x219BD4), 0x87A500DE)   # lh a1,0xDE(sp)
    struct.pack_into('<I', data, fo(0x219BE4), 0x87A500DE)   # lh a1,0xDE(sp)
    struct.pack_into('<I', data, fo(0x219CA0), 0x87A400DE)   # lh a0,0xDE(sp)
    struct.pack_into('<I', data, fo(0x219DAC), 0x93A200DD)   # lbu v0,0xDD(sp)
    struct.pack_into('<I', data, fo(0x219DB0), 0x02028021)   # addu s0,s0,v0
    # F3: 图标码比较立即数 → 正值
    for va, now in ((0x219C08, 0x240300B5), (0x219C14, 0x240300B1),
                    (0x219C94, 0x240300B5), (0x219CAC, 0x240300B1),
                    (0x219D24, 0x240200B5), (0x219D38, 0x240200B1)):
        struct.pack_into('<I', data, fo(va), now)
    # CharWidth / CCTC
    put(0x21AD18, [0x08000000 | (((CAVE+OFF_CW)>>2) & 0x3FFFFFF), 0])
    put(0x21ADE0, [0x08000000 | (((CAVE+OFF_CCTC)>>2) & 0x3FFFFFF), 0])
    # StringWidth: 跳 cave; 原 tail (kerning/返回) 废弃为 nop (kerning 已入 cave)
    put(0x21AC74, [0x08000000 | (((CAVE+OFF_SW)>>2) & 0x3FFFFFF)])
    struct.pack_into('<I', data, fo(0x21AC78), 0x02003021)   # delay: addu a2,s0,zero
    for va in range(0x21AC7C, 0x21ACA4, 4):
        struct.pack_into('<I', data, fo(va), 0)

    ndiff = sum(1 for x, y in zip(orig, bytes(data)) if x != y)
    print('改动字节: %d' % ndiff)
    open(DST, 'wb').write(bytes(data))
    print('写出', DST)

    dis4.main = bytes(data)[SEC_OFF:SEC_OFF + 0x4DED00]
    print('\n=== DrawString 取字符/循环尾 ===')
    print(dis4.dis(0x219BC4, 0x1C)); print(dis4.dis(0x219DAC, 0xC))
    print('\n=== CharWidth 头 / CCTC 头 / StringWidth 跳转区 ===')
    print(dis4.dis(0x21AD10, 0x10)); print(dis4.dis(0x21ADE0, 0x8)); print(dis4.dis(0x21AC6C, 0x3C))
    print('\n=== cave sw (新版, 无栈帧) ==='); print(dis4.dis(CAVE+OFF_SW, len(w_sw)*4))
    print('\n=== cave cctc (v2) ==='); print(dis4.dis(CAVE+OFF_CCTC, len(w_cc)*4))

if __name__ == '__main__':
    main()
