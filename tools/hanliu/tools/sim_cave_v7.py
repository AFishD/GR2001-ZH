# [hanliu 收编] 原件: C:/gr_build/tmp/zh8b/sim_cave_v7.py (逐字复制)。原件保留于原处未动。
# -*- coding: utf-8 -*-
"""sim_cave_v7.py — SLUS_P_V7 四 cave 的字面模拟器 (v6 sim_cave.py 的 v7 版, 延迟槽语义正确)

v7 变更: cw 直 UV 分支返回恒定 CELL_W (不乘 RSFont+0x1C 样式 scaleX)。

测试向量断言:
  A. ds16: lead A1..AD 成对 (v5 标记制扩容), 其余单字节; char16/步长正确
  B. cw:   对: idx<mSize → 记录宽×scale; idx≥mSize → 恒 12 (与 scale 无关 ← v7 语义)
           ASCII/图标/空格不变; 记录路径 ×scale 行为保持 (1.64→26, 0.5→8)
  C. cctc: 对: idx<mSize → 记录 UV; idx≥mSize → 直接UV (u0=0+12c, v0=128+15r, u1=+12, v1=+15)
  D. sw:   对字符: s1 += 宽, s4 += 2 (v5 语义)
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys

ELF = os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_V7.elf')
SEC_OFF, SEC_ADDR = 0x80, 0x00100000
fo = lambda va: SEC_OFF + va - SEC_ADDR
ELF_DATA = open(ELF, 'rb').read()
def rd32(va): return struct.unpack_from('<I', ELF_DATA, fo(va))[0]

CAVE = 0x26BEA0
A_DS, A_CW, A_CCTC, A_SW = CAVE + 0x000, CAVE + 0x070, CAVE + 0x180, CAVE + 0x25C
RET = 0xDEADC0DE

def s32(v): return v - (1 << 32) if v >= 0x80000000 else v
def f32b(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def b2f(v): return struct.unpack('<f', struct.pack('<I', v & 0xFFFFFFFF))[0]

class Mem:
    def __init__(self): self.seg = {}
    def region(self, base, size): self.seg[base] = bytearray(size); return base
    def _f(self, a):
        for b, arr in self.seg.items():
            if b <= a < b + len(arr): return arr, a - b
        raise KeyError('unmapped 0x%08X' % a)
    def r8(self, a): arr, o = self._f(a); return arr[o]
    def w8(self, a, v): arr, o = self._f(a); arr[o] = v & 0xFF
    def r16(self, a): return self.r8(a) | (self.r8(a + 1) << 8)
    def w16(self, a, v): self.w8(a, v); self.w8(a + 1, v >> 8)
    def r32(self, a): return self.r16(a) | (self.r16(a + 2) << 16)
    def w32(self, a, v): self.w16(a, v & 0xFFFF); self.w16(a + 2, (v >> 16) & 0xFFFF)
    def r64(self, a): return self.r32(a) | (self.r32(a + 4) << 32)

class CPU:
    def __init__(self, mem, entry, **regs):
        self.m = mem
        self.r = [0] * 32
        self.f = [0] * 32
        self.hi = self.lo = 0
        self.pc = entry
        names = ['zero','at','v0','v1','a0','a1','a2','a3','t0','t1','t2','t3','t4','t5',
                 't6','t7','s0','s1','s2','s3','s4','s5','s6','s7','t8','t9','k0','k1',
                 'gp','sp','fp','ra']
        for k, v in regs.items():
            self.r[names.index(k)] = v & 0xFFFFFFFF
    def run(self, max_steps=500, stop=None, stop_multi=None):
        stops = stop_multi or ((stop,) if stop is not None else ())
        for _ in range(max_steps):
            if self.pc == RET: return
            if self.pc in stops: return
            if self.pc == 0x00118EE0:            # fptosi 桩: v0 = int(trunc f12)
                self.r[2] = int(b2f(self.f[12])) & 0xFFFFFFFF
                self.pc = self.r[31]
                continue
            self.step()
        raise AssertionError('runaway @0x%08X' % self.pc)
    def step(self):
        w = rd32(self.pc); cur = self.pc
        r = self.r
        op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31
        rd_ = (w >> 11) & 31; sa = (w >> 6) & 31; fn = w & 63
        imm = w & 0xFFFF; simm = imm - 0x10000 if imm >= 0x8000 else imm
        jump = None
        def wreg(i, v): r[i] = v & 0xFFFFFFFF
        if w == 0:
            pass
        elif op == 0x00:
            if fn == 0x00: wreg(rd_, r[rt] << sa)
            elif fn == 0x02: wreg(rd_, (r[rt] & 0xFFFFFFFF) >> sa)
            elif fn == 0x08: jump = r[rs]
            elif fn == 0x10: wreg(rd_, self.hi)
            elif fn == 0x12: wreg(rd_, self.lo)
            elif fn == 0x18:
                self.lo = (r[rs] * r[rt]) & 0xFFFFFFFF
                if rd_: wreg(rd_, self.lo)
            elif fn == 0x1A:
                a, b = s32(r[rs]), s32(r[rt])
                assert b != 0, 'div by 0'
                q = abs(a) // abs(b)
                if (a < 0) != (b < 0): q = -q
                self.lo = q & 0xFFFFFFFF
                if rd_: wreg(rd_, self.lo)
            elif fn == 0x21: wreg(rd_, r[rs] + r[rt])
            elif fn == 0x23: wreg(rd_, r[rs] - r[rt])
            elif fn == 0x25: wreg(rd_, r[rs] | r[rt])
            elif fn == 0x2A: wreg(rd_, 1 if s32(r[rs]) < s32(r[rt]) else 0)
            elif fn == 0x2B: wreg(rd_, 1 if r[rs] < r[rt] else 0)
            else: raise AssertionError('special fn=%x @%08X' % (fn, cur))
        elif op == 0x02: jump = ((cur + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2)
        elif op == 0x03: jump = ((cur + 4) & 0xF0000000) | ((w & 0x3FFFFFF) << 2); wreg(31, cur + 8)
        elif op == 0x04:
            if r[rs] == r[rt]: jump = cur + 4 + (simm << 2)
        elif op == 0x05:
            if r[rs] != r[rt]: jump = cur + 4 + (simm << 2)
        elif op == 0x09: wreg(rt, r[rs] + simm)
        elif op == 0x0B: wreg(rt, 1 if r[rs] < (imm & 0xFFFFFFFF) else 0)
        elif op == 0x0C: wreg(rt, r[rs] & imm)
        elif op == 0x11:
            if rs == 4: self.f[rd_] = r[rt]                      # mtc1 rt, fs
            elif rs == 0x14:                                     # cvt.s.w fd, fs
                self.f[sa] = f32b(float(s32(self.f[rt])))
            elif rs == 0x10:                                     # mul.s fd, fs, ft
                a = b2f(self.f[rt]); b = b2f(self.f[rd_])
                self.f[sa] = f32b(a * b)
            else: raise AssertionError('cop1 rs=%x @%08X' % (rs, cur))
        elif op == 0x20: wreg(rt, (self.m.r8(r[rs] + simm) ^ 0x80) - 0x80)
        elif op == 0x23: wreg(rt, self.m.r32(r[rs] + simm))
        elif op == 0x24: wreg(rt, self.m.r8(r[rs] + simm))
        elif op == 0x25: wreg(rt, self.m.r16(r[rs] + simm))
        elif op == 0x28: self.m.w8(r[rs] + simm, r[rt])
        elif op == 0x29: self.m.w16(r[rs] + simm, r[rt])
        elif op == 0x2B: self.m.w32(r[rs] + simm, r[rt])
        elif op == 0x31: self.f[rt] = self.m.r32(r[rs] + simm)
        elif op == 0x39: self.m.w32(r[rs] + simm, self.f[rt])
        elif op == 0x37: wreg(rt, self.m.r64(r[rs] + simm))
        elif op == 0x3F:
            self.m.w32(r[rs] + simm, r[rt]); self.m.w32(r[rs] + simm + 4, r[rt + 1] if False else (r[rt] >> 32))
            # 64 位存: 用两个 32 位 (高 32 位在 64 位寄存器模拟中取 0)
        else: raise AssertionError('op=%x @%08X' % (op, cur))
        if jump is None:
            self.pc = cur + 4
        else:
            # 真延迟槽: 执行 cur+4 处指令 (不允许其中再跳)
            dpc = cur + 4
            w2 = rd32(dpc)
            self._delay_exec(w2, dpc)
            self.pc = jump
    def _delay_exec(self, w, cur):
        r = self.r
        op = w >> 26; rs = (w >> 21) & 31; rt = (w >> 16) & 31
        imm = w & 0xFFFF; simm = imm - 0x10000 if imm >= 0x8000 else imm
        if w == 0: return
        if op == 0x09: r[rt] = (r[rs] + simm) & 0xFFFFFFFF
        elif op == 0x0C: r[rt] = r[rs] & imm
        elif op == 0x23: r[rt] = self.m.r32(r[rs] + simm)
        elif op == 0x24: r[rt] = self.m.r8(r[rs] + simm)
        elif op == 0x2B: self.m.w32(r[rs] + simm, r[rt])
        elif op == 0x39: self.m.w32(r[rs] + simm, self.f[rt])
        else: raise AssertionError('delay slot op=%x @%08X 未建模' % (op, cur))

# ---------------- 假字体内存 ----------------
def rec(pad, adv, u0, v0, u1, v1): return (pad, adv, u0, v0, u1, v1)

def setup_font(kd_recs, msize, scale=1.0, space_w=10):
    mem = Mem()
    mem.region(0x01000000, 0x100)               # RSFont
    mem.region(0x01010000, 0x100)               # FD
    mem.region(0x01020000, max(64, msize * 10)) # KD
    mem.region(0x7EFFE000, 0x3000)              # 栈 (sp=0x7F000000, 帧向下)
    mem.w32(0x7F000000, RET)
    mem.w32(0x01000014, space_w)
    mem.w32(0x0100001C, f32b(scale))
    mem.w8(0x01000024, 0)
    mem.w32(0x01000028, 0x01010000)
    mem.w32(0x01010020, 0x20)
    mem.w32(0x01010038, 0x01020000)
    mem.w32(0x01010044, msize)
    for i, rr in enumerate(kd_recs[:msize]):
        pad, adv, u0, v0, u1, v1 = rr
        mem.w32(0x01020000 + 10 * i, (pad & 0xFF) | (adv << 8) | (u0 << 16))
        mem.w16(0x01020000 + 10 * i + 4, v0)
        mem.w16(0x01020000 + 10 * i + 6, u1)
        mem.w16(0x01020000 + 10 * i + 8, v1)
    return mem

def call_ds16(char_bytes, str_addr, i, strlen):
    mem = Mem()
    mem.region(0x70000000, 0x1000)
    base = str_addr & ~0xFFF
    mem.region(base, 0x2000)
    for k, b in enumerate(char_bytes):
        mem.w8(str_addr + k, b)
    a0 = 0x700000DE
    cpu = CPU(mem, A_DS, a0=a0, a1=char_bytes[i], s6=str_addr, s0=i, s7=strlen, ra=RET)
    cpu.run()
    return mem.r16(a0), mem.r8(a0 - 1)

def call_cw(mem, ch):
    cpu = CPU(mem, A_CW, a0=0x01000000, a1=ch & 0xFFFFFFFF, sp=0x7F000000, ra=RET)
    cpu.run()
    return s32(cpu.r[2])

def call_cctc(mem, ch):
    mem.region(0x71000000, 0x100)
    p = [0x71000000, 0x71000004, 0x71000008, 0x7100000C]
    cpu = CPU(mem, A_CCTC, a0=0x01000000, a1=ch & 0xFFFFFFFF,
              a2=p[0], a3=p[1], t0=p[2], t1=p[3], sp=0x7F000000, ra=RET)
    cpu.run(stop=0x21AE20)
    if cpu.pc == 0x21AE20:
        return ('REC', cpu.r[5], cpu.r[10])   # (resume, a1=idx, t2=KD)
    return [b2f(mem.r32(x)) for x in p]

def call_sw(mem, first_byte, second, str_addr):
    base = str_addr & ~0xFFF
    mem.region(base, 0x2000)
    mem.w8(str_addr, first_byte); mem.w8(str_addr + 1, second)
    cpu = CPU(mem, A_SW, a0=0x01000000, a1=first_byte, v0=str_addr, s0=8, s4=0, s1=0,
              s3=0x01000000, sp=0x7F000000, ra=RET)
    cpu.run(stop_multi=(0x21AC84, 0x21AC7C))
    tag = {0x21AC84: 'PAIR', 0x21AC7C: 'ORIG'}[cpu.pc]
    return (tag, s32(cpu.r[17]), s32(cpu.r[20]))

# ============================ 测试 ============================
def main():
    fail = 0
    global kd8f
    kd8f = None
    def chk(name, got, want):
        nonlocal fail
        if got != want:
            fail += 1
            print('  FAIL %s: got %r want %r' % (name, got, want))

    print('[A] ds16')
    S = 0x60000000
    s = bytes([0xB5, 0x20, 0xA1, 0xA1, 0xAE, 0xA2, 0xA9, 0xD2, 0xAD, 0xFE, 0xA1, 0x20, 0xA1])
    chk('lead B5→单', call_ds16(s, S, 0, len(s)), (0x00B5, 1))
    chk('space→单', call_ds16(s, S, 1, len(s)), (0x0020, 1))
    chk('(A1,A1)→对', call_ds16(s, S, 2, len(s)), (0xA1A1, 2))
    chk('末尾A1→单', call_ds16(s, S, 12, len(s)), (0x00A1, 1))
    chk('lead AE→单(上界)', call_ds16(bytes([0xAE, 0xA2]), S, 0, 2), (0x00AE, 1))
    chk('lead AD→对', call_ds16(bytes([0xAD, 0xFE]), S, 0, 2), (0xADFE, 2))
    chk('lead A9→对', call_ds16(s, S, 6, len(s)), (0xA9D2, 2))
    chk('trail 0xA0→单', call_ds16(bytes([0xA1, 0xA0]), S, 0, 2), (0x00A1, 1))
    chk('trail 0xFF→单', call_ds16(bytes([0xA1, 0xFF]), S, 0, 2), (0x00A1, 1))

    print('[B] cw')
    kd8 = [rec(0, 10, 0, 0, 0, 0)] * 416
    kd8[384] = rec(0, 16, 3, 4, 19, 18)
    kd8[0x41 - 0x20] = rec(0, 12, 50, 60, 62, 76)
    globals()['kd8f'] = kd8
    m8 = setup_font(kd8, 416)
    chk('DB8 对(A2,E3)→16', call_cw(m8, 0xA2E3), 16)
    chk('DB8 ASCII A→12', call_cw(m8, 0x41), 12)
    chk('图标 B5→20', call_cw(m8, 0xB5), 20)
    chk('图标 B1→20', call_cw(m8, 0xB1), 20)
    chk('空格→10', call_cw(m8, 0x20), 10)
    kdz = [rec(0, 10, 0, 0, 0, 0)] * 224
    mz = setup_font(kdz, 224)
    chk('ZH8 对(A1,A1)→12', call_cw(mz, 0xA1A1), 12)
    chk('ZH8 对(AD,FE)→12', call_cw(mz, 0xADFE), 12)
    chk('ZH8 越外对(A9,D2)→12', call_cw(mz, 0xA9D2), 12)
    # --- v7 核心语义: 直 UV 宽与样式 scaleX 无关 ---
    m9 = setup_font(kdz, 224, scale=0.5)
    chk('ZH8 对 scale0.5→12(v7)', call_cw(m9, 0xA1A1), 12)
    ml = setup_font(kdz, 224, scale=1.64)
    chk('ZH8 对 scale1.64→12(v7)', call_cw(ml, 0xA1A1), 12)
    chk('ZH8 对(AD,FE) scale1.64→12(v7)', call_cw(ml, 0xADFE), 12)
    mh = setup_font(kdz, 224, scale=0.8)
    chk('ZH8 对 scale0.8→12(v7)', call_cw(mh, 0xA1A1), 12)
    # --- 记录路径保持 ×scale (原版语义, DB8 回归零损伤) ---
    m8l = setup_font(kd8, 416, scale=1.64)
    chk('DB8 对 scale1.64→26(记录)', call_cw(m8l, 0xA2E3), 26)
    chk('DB8 ASCII scale1.64→19(记录)', call_cw(m8l, 0x41), 19)
    m8s = setup_font(kd8, 416, scale=0.5)
    chk('DB8 对 scale0.5→8(记录)', call_cw(m8s, 0xA2E3), 8)

    print('[C] cctc')
    uv = call_cctc(m8, 0xA2E3)
    chk('DB8 对→记录路径 idx', uv, ('REC', 384, 0x01020000))
    chk('DB8 对 idx384 记录UV', [uv[1]] and [3.0, 4.0, 19.0, 18.0],
        [kd8f[384][2], kd8f[384][3], kd8f[384][4], kd8f[384][5]])
    uv = call_cctc(mz, 0xA1A1)
    chk('对(A1,A1) slot0', [round(x, 3) for x in uv], [0.0, 128.0, 12.0, 143.0])
    uv = call_cctc(mz, 0xA1A2)
    chk('对(A1,A2) slot1', [round(x, 3) for x in uv], [12.0, 128.0, 24.0, 143.0])
    uv = call_cctc(mz, 0xA2A1)
    chk('对(A2,A1) slot94 row2col12', [round(x, 3) for x in uv], [144.0, 158.0, 156.0, 173.0])
    uv = call_cctc(mz, 0xA8A2)
    chk('对(A8,A2) slot659 row16col3', [round(x, 3) for x in uv], [36.0, 368.0, 48.0, 383.0])
    uv = call_cctc(mz, 0xADFE)
    chk('对(AD,FE) slot1221 (越界槽, 仅数学)', [round(x, 3) for x in uv], [384.0, 563.0, 396.0, 578.0])
    uv = call_cctc(m8, 0x41)
    chk('ASCII→记录路径 idx', uv, ('REC', 0x21, 0x01020000))

    print('[D] sw')
    chk('DB8 对 sw', call_sw(m8, 0xA2, 0xE3, S), ('PAIR', 16, 2))
    chk('ZH8 对 sw', call_sw(mz, 0xA1, 0xA1, S), ('PAIR', 12, 2))
    chk('ZH8 对(AD,FE) sw', call_sw(mz, 0xAD, 0xFE, S), ('PAIR', 12, 2))
    chk('ZH8 对 sw scale1.64→12(v7)', call_sw(ml, 0xA1, 0xA1, S), ('PAIR', 12, 2))
    chk('ZH8 ASCII sw→orig 路径', call_sw(mz, 0x41, 0x00, S)[0], 'ORIG')

    print('[SIM] %s (fail=%d)' % ('PASS' if fail == 0 else 'FAIL', fail))
    return 1 if fail else 0

if __name__ == '__main__':
    sys.exit(main())
