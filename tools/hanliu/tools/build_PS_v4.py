# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/build_PS_v4.py (逐字复制 (lhu 修复 -> SLUS_P_T, GR_DB7 实证))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""build_PS_v4.py — P-T: P-S + 字符槽零扩展修复 (lh → lhu)
根因 (2026-09-12 排查结论): P-S 的三个字符槽加载用 lh (符号扩展), char16 ≥ 0x8000 时
a1 = 0xFFFFFFFFFFFFA1A1; cw/cctc cave 入口 `srl t0, a1, 8` 得 0x00FFFFA1 → idx 公式算出
垃圾值 ≥ mSize → 每对 clamp 到记录 0 (空格) → 全部对渲染为空格宽度的"短横"条
(空格格双线性边缘渗漏, 与 face 放置无关)。此前误判为"字节对验收器"。
修复: 0x219BD4/0x219BE4 lh a1 → lhu a1; 0x219CA0 lh a0 → lhu a0 (3 词, cave 不动)。
ASCII 路径不变 (ds16 存 0x00XX, lhu==lh); 0x92 等高位单字节经 cave andi 0xFF 后亦不变。
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct

SRC = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
DST = os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'SLUS_P_T.elf')
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
Asm = ns['Asm']; build_ds16 = ns['build_ds16']; build_cw = ns['build_cw']; build_cctc = ns['build_cctc']; lead_checks = ns['lead_checks']
R = ns['R']

CAVE = 0x26BEA0
OFF_DS, OFF_CW, OFF_CCTC, OFF_SW = 0x000, 0x09C, 0x184, 0x1E8

a_ds = Asm(); build_ds16(a_ds); w_ds = a_ds.resolve(CAVE + OFF_DS)
a_cw = Asm(); build_cw(a_cw); w_cw = a_cw.resolve(CAVE + OFF_CW)
a_cc = Asm(); build_cctc(a_cc, 0x21AE20); w_cc = a_cc.resolve(CAVE + OFF_CCTC)

def build_sw_min(a, charwidth):
    ORIG = 0x0021AC7C
    LOOP = 0x0021AC84
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
# DrawString v1 → 16 位槽位 (★v4: lh → lhu 零扩展)
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
# 与 P-S 的差异应恰为 3 词中的 3 字节 (lh 0x87→lhu 0x97)
ps = open(os.path.join(REPO_ROOT, 'archive', 'elf_lineage', 'SLUS_P_S.elf'), 'rb').read()
dif_ps = [i for i in range(len(data)) if ps[i] != data[i]]
print('P-T vs 原版 改动=%dB; vs P-S 差异字节=%d @%s' % (ndiff, len(dif_ps), [hex(x) for x in dif_ps]))
assert all(any(fo(va) <= i < fo(va) + 4 for va in (0x219BD4, 0x219BE4, 0x219CA0)) for i in dif_ps), dif_ps
open(DST, 'wb').write(bytes(data))
print('写出', DST)
