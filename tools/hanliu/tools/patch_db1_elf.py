# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/patch_db1_elf.py (逐字复制 (Stage1 synth-byte ELF 补丁))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""patch_db1_elf.py — Stage1 DBCS ELF 补丁 (synth-byte 方案, 仅 DrawString v1 主循环)

原理 (见 han_v2/ELF_DBCS_PATCH.md):
  DrawString v1 (0x219A70) 是唯一带字符循环的绘制入口 (v2 0x219E00 / v3 0x219EB0 均委托 v1)。
  循环取字符处原为: jal 0x40BFC8(恒等存储) + delay(addiu a0,sp,0xDF) + lb a1,0xDF(sp)。
  替换 jal 为 cave 翻译例程: 若 s[i]∈[0xA1,0xFE] 且非保留码 {0xAE,0xB1,0xB5,0xE7,0xF1}
  且 s[i+1]∈[0xA1,0xFE] → 合成字节 synth=((lead-0xA1)*94+(trail-0xA1)+161)&0xFF 写回 [sp+0xDF],
  并在 [sp+0xDE] 写步长 2; 否则写原字节、步长 1。
  循环尾部原 addiu s0,s0,1 换成 lbu v0,0xDE(sp) + addu s0,s0,v0 → DBCS 一次消费 2 字节。
  CharWidth/ComputeCharTextureCoords 零改动 (synth 字节走原索引公式)。
  EN 文本高位字节仅 {0x92,0xAE,0xB1,0xB5,0xE7,0xF1}, 全部不在 lead 检测范围 → 英文零影响。

cave: 0x26BEA0..0x26C18F (748B) = FindPropertyForModelID(432B)+FindPropertyForID(316B)
  两函数全镜像零引用 (jal/j/绝对字/lui+ori 四重扫描), 判死代码, 覆写安全。
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys

sys.path.insert(0, os.path.join(REPO_ROOT, 'work', 'tmp', 'slus_scan'))
import dis4

SRC = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
DST = os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'SLUS_db1.elf')

SEC_OFF, SEC_ADDR = 0x80, 0x00100000

R = {'zero':0,'at':1,'v0':2,'v1':3,'a0':4,'a1':5,'a2':6,'a3':7,
     't0':8,'t1':9,'t2':10,'t3':11,'t4':12,'t5':13,'t6':14,'t7':15,
     's0':16,'s1':17,'s2':18,'s3':19,'s4':20,'s5':21,'s6':22,'s7':23,
     't8':24,'t9':25,'k0':26,'k1':27,'gp':28,'sp':29,'fp':30,'ra':31}

def I(op, rs=0, rt=0, rd=0, sa=0, fn=0, imm=0, tgt=None):
    if tgt is not None:
        imm = tgt  # branch: instruction index delta, resolved by asm()
    g = lambda k: R[k] if isinstance(k, str) else k
    return (op<<26)|(g(rs)<<21)|(g(rt)<<16)|(g(rd)<<11)|(sa<<6)|(fn&0x3F) | (imm & 0xFFFF)

def enc_j(addr, pc):
    assert (addr & 0xF0000000) == (pc & 0xF0000000), 'j/jal 跨 256MB 段'
    return 0x0C000000 | ((addr >> 2) & 0x3FFFFFF)

def asm(start_va, seq):
    """seq: list of ('i', word) 或 ('b', op, rs, rt, target_index) (beq/bne)"""
    words = []
    for it in seq:
        if it[0] == 'i':
            words.append(it[1])
        else:
            _, op, rs, rt, ti = it
            delta = ti - (len(words) + 1)
            assert -0x8000 <= delta < 0x8000
            words.append((op<<26)|(R[rs]<<21)|(R[rt]<<16)|(delta & 0xFFFF))
    return words

CAVE = 0x26BEA0

def build_cave():
    DONE = 40  # index of DONE label
    seq = [
        ('i', I(0x28, rs='a0', rt='a1', imm=0)),        # i0  sb a1,0(a0)      默认 char=lead
        ('i', I(0x0C, rs='a1', rt='t0', imm=0xFF)),     # i1  andi t0,a1,0xFF
        ('i', I(0x09, rs='zero', rt='v0', imm=1)),      # i2  addiu v0,zero,1  step=1
        ('i', I(0x0B, rs='t0', rt='t1', imm=0xA1)),     # i3  sltiu t1,t0,0xA1
        ('b', 0x05, 't1', 'zero', DONE),                # i4  bne t1,zero,DONE lead<0xA1 → 单字节
        ('i', 0x00000000),                              # i5  nop
        ('i', I(0x0B, rs='t0', rt='t1', imm=0xFF)),     # i6  sltiu t1,t0,0xFF
        ('b', 0x04, 't1', 'zero', DONE),                # i7  beq t1,zero,DONE lead>=0xFF → 单字节
        ('i', 0x00000000),                              # i8  nop
        ('i', I(0x09, rs='zero', rt='t1', imm=0xAE)),   # i9  保留码 5 连检
        ('b', 0x04, 't0', 't1', DONE),                  # i10 beq t0,t1,DONE  0xAE(®)
        ('i', I(0x09, rs='zero', rt='t1', imm=0xB1)),   # i11 (delay, 常执行)
        ('b', 0x04, 't0', 't1', DONE),                  # i12                 0xB1(±)
        ('i', I(0x09, rs='zero', rt='t1', imm=0xB5)),   # i13
        ('b', 0x04, 't0', 't1', DONE),                  # i14                 0xB5(µ)
        ('i', I(0x09, rs='zero', rt='t1', imm=0xE7)),   # i15
        ('b', 0x04, 't0', 't1', DONE),                  # i16                 0xE7(ç)
        ('i', I(0x09, rs='zero', rt='t1', imm=0xF1)),   # i17
        ('b', 0x04, 't0', 't1', DONE),                  # i18                 0xF1(ñ)
        ('i', I(0x09, rs='s7', rt='t8', imm=-1 & 0xFFFF)),    # i19 addiu t8,s7,-1  len-1
        ('i', I(0x00, rs='s0', rt='t8', rd='t8', fn=0x2A)),   # i20 slt  t8,s0,t8   i < len-1 ?
        ('b', 0x04, 't8', 'zero', DONE),                # i21 beq t8,zero,DONE 末字符 → 单字节 (越界读防护)
        ('i', 0x00000000),                              # i22 nop
        ('i', I(0x00, rs='s6', rt='s0', rd='t7', fn=0x21)),   # i23 daddu t7,s6,s0  ptr=str+i
        ('i', I(0x24, rs='t7', rt='t3', imm=1)),        # i24 lbu t3,1(t7)    trail (仅 lead 合法 + 未越界才读)
        ('i', I(0x0B, rs='t3', rt='t1', imm=0xA1)),     # i21 sltiu t1,t3,0xA1
        ('b', 0x05, 't1', 'zero', DONE),                # i22 bne t1,zero,DONE trail<0xA1
        ('i', 0x00000000),                              # i23 nop
        ('i', I(0x0B, rs='t3', rt='t1', imm=0xFF)),     # i24 sltiu t1,t3,0xFF
        ('b', 0x04, 't1', 'zero', DONE),                # i25 beq t1,zero,DONE trail=0xFF 禁用
        ('i', 0x00000000),                              # i26 nop
        ('i', I(0x09, rs='t0', rt='t4', imm=-0xA1 & 0xFFFF)),  # i27 addiu t4,t0,-0xA1
        ('i', I(0x09, rs='t3', rt='t5', imm=-0xA1 & 0xFFFF)),  # i28 addiu t5,t3,-0xA1
        ('i', I(0x09, rs='zero', rt='t6', imm=94)),     # i29 addiu t6,zero,94
        ('i', I(0x00, rs='t4', rt='t6', rd='t6', fn=0x18)),    # i30 mult t6,t4,t6 (EE 三操作数)
        ('i', I(0x00, rs='t6', rt='t5', rd='t6', fn=0x21)),    # i31 addu t6,t6,t5
        ('i', I(0x09, rs='t6', rt='t6', imm=161)),      # i32 addiu t6,t6,161 (+129+32)
        ('i', I(0x0C, rs='t6', rt='t6', imm=0xFF)),     # i33 andi t6,t6,0xFF
        ('i', I(0x28, rs='a0', rt='t6', imm=0)),        # i34 sb t6,0(a0)     synth char
        ('i', I(0x09, rs='zero', rt='v0', imm=2)),      # i35 addiu v0,zero,2 step=2
        # DONE (i36):
        ('i', I(0x28, rs='a0', rt='v0', imm=-1 & 0xFFFF)),     # i36 sb v0,-1(a0)  step → [sp+0xDE]
        ('i', I(0x00, rs='ra', fn=0x08)),               # i37 jr ra
        ('i', 0x00000000),                              # i38 nop
    ]
    return asm(CAVE, seq)

def main():
    data = bytearray(open(SRC, 'rb').read())
    orig = bytes(data)

    def rd(va):
        return struct.unpack_from('<I', data, SEC_OFF + va - SEC_ADDR)[0]

    # ---- 断言: 补丁点原值 ----
    assert rd(0x219BCC) == 0x0C102FF2, hex(rd(0x219BCC))   # jal 0x40BFC8
    assert rd(0x219BD0) == 0x27A400DF                     # delay: addiu a0,sp,0xDF (保留)
    assert rd(0x219DAC) == 0x00000000                     # nop
    assert rd(0x219DB0) == 0x26100001                     # addiu s0,s0,1
    # cave 区域原值 = 两死函数代码, 抽查前 4 字
    assert rd(CAVE) == 0x27BDFEE0, '%08X' % rd(CAVE)      # addiu sp,sp,-0x120
    for va in range(CAVE, CAVE + 748, 4):
        pass  # 全区覆写, 无需保真

    # ---- patch 1: 取字符处 jal → cave ----
    struct.pack_into('<I', data, SEC_OFF + 0x219BCC - SEC_ADDR, enc_j(CAVE, 0x219BCC))
    # ---- patch 2/3: 循环尾步长 ----
    struct.pack_into('<I', data, SEC_OFF + 0x219DAC - SEC_ADDR, 0x93A200DE)  # lbu v0,0xDE(sp)
    struct.pack_into('<I', data, SEC_OFF + 0x219DB0 - SEC_ADDR, 0x02028021)  # addu s0,s0,v0 (rs=s0,rt=v0,rd=s0)
    # ---- cave 覆写 ----
    cave_words = build_cave()
    assert len(cave_words) * 4 <= 748, len(cave_words)
    for k, w in enumerate(cave_words):
        struct.pack_into('<I', data, SEC_OFF + CAVE - SEC_ADDR + 4 * k, w)

    ndiff = sum(1 for a, b in zip(orig, bytes(data)) if a != b)
    print('改动字节: %d (3 指令 + cave %d 指令)' % (ndiff, len(cave_words)))
    open(DST, 'wb').write(bytes(data))
    print('写出', DST, len(data), 'B')

    # ---- 自验: 用 dis4 反汇编补丁后镜像 (替换其内存镜像) ----
    dis4.main = bytes(data)[SEC_OFF:SEC_OFF + 0x4DED00]
    print('\n=== 补丁点反汇编 (DrawString v1 循环头) ===')
    for line in dis4.dis(0x219BC0, 0x28).splitlines():
        print(line)
    print('\n=== 循环尾 ===')
    for line in dis4.dis(0x219D88, 0x34).splitlines():
        print(line)
    print('\n=== cave (0x26BEA0) ===')
    for line in dis4.dis(CAVE, len(cave_words) * 4).splitlines():
        print(line)

if __name__ == '__main__':
    main()
