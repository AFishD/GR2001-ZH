# -*- coding: utf-8 -*-
r"""p02_elf_icon_scan.py — round42 步骤②: 在 ELF 里找「图标字节」比较点 + 图标条 UV 常量 (只读)

两条线索:
  A) 原版 DrawString v1 (0x219A70) 里对**字符值**的立即数比较 =
        addiu v1, zero, -75  (0xFFFFFFB5) → 字符 == 0xB5
        addiu v1, zero, -79  (0xFFFFFFB1) → 字符 == 0xB1
     ⇒ 全 ELF 扫 `addiu rt, $zero, imm` 且 imm ∈ 0xFF80..0xFFFF (= 有符号字节 0x80..0xFF),
       这些就是「拿某个高位字节当特殊字符判」的候选点。
  B) 图标 UV 常量: 0xB5 → (1,198)-(21,218); 0xB1 → (25,198)-(45,218)
     ⇒ 扫 lui rt, imm 里 imm ∈ {0x3F80(1.0) 0x41A8(21.0) 0x41C8(25.0) 0x4234(45.0)
        0x4346(198.0) 0x435A(218.0) 0x41A0(20.0) 0x4248(50.0) 0x428C(70.0)},
       并按地址聚类 (同一段代码里的多个常量 = 一处 UV 硬编码)。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ELF = os.path.join(REPO, 'third_party', 'orig', 'ps2', 'slus_out', 'SLUS_206.13')
SEC_OFF, SEC_ADDR, SEC_SIZE = 0x80, 0x00100000, 0x4DED00

data = open(ELF, 'rb').read()
seg = data[SEC_OFF:SEC_OFF + SEC_SIZE]
R = ['$zero', '$at', '$v0', '$v1', '$a0', '$a1', '$a2', '$a3', '$t0', '$t1', '$t2', '$t3',
     '$t4', '$t5', '$t6', '$t7', '$s0', '$s1', '$s2', '$s3', '$s4', '$s5', '$s6', '$s7',
     '$t8', '$t9', '$k0', '$k1', '$gp', '$sp', '$fp', '$ra']

# 符号表 (与 tools/diag/dis_ee.py 同口径)
strtab = data[0x4DEDE0:0x4DEDE0 + 0x13E199]
syms, p, end = {}, 0x61CF80, 0x61CF80 + 0x97420
while p < end and p + 16 <= len(data):
    name, value, size, info, other, shndx = struct.unpack_from('<IIIBBH', data, p)
    p += 16
    if name and value and SEC_ADDR <= value < SEC_ADDR + SEC_SIZE:
        syms.setdefault(value, strtab[name:strtab.index(b'\0', name)].decode('latin-1'))
keys = sorted(syms)


def fname(va):
    import bisect
    i = bisect.bisect_right(keys, va) - 1
    if i >= 0:
        k = keys[i]
        if 0 <= va - k < 0x8000:
            return '%s+0x%X' % (syms[k], va - k)
    return 'sub_%08X' % va


def word(va):
    return struct.unpack_from('<I', seg, va - SEC_ADDR)[0]


print('=' * 78)
print('A) 全 ELF: addiu rt,$zero,imm 且 imm∈0xFF80..0xFFFF (把高位字节当特殊字符判)')
print('   基线: 原版 DrawString v1 @0x219C08/0x219C10 = -75(0xB5), @0x219C14 = -79(0xB1)')
print('=' * 78)
hits = []
for off in range(0, SEC_SIZE, 4):
    w = struct.unpack_from('<I', seg, off)[0]
    if (w >> 26) != 0x09:                     # addiu
        continue
    rs, rt, imm = (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
    if rs != 0 or not (0xFF80 <= imm <= 0xFFFF):
        continue
    hits.append((SEC_ADDR + off, rt, imm))
print('   命中 %d 处:' % len(hits))
for va, rt, imm in hits:
    print('     %08X  addiu %-6s $zero, %-6d (0x%04X → 字节 0x%02X)   %s'
          % (va, R[rt], imm - 0x10000, imm, imm & 0xFF, fname(va)))

print()
print('=' * 78)
print('B) 图标条 UV 常量扫描 (lui rt, imm)')
print('=' * 78)
FLOATS = {0x3F80: 1.0, 0x41A0: 20.0, 0x41A8: 21.0, 0x41C8: 25.0, 0x4234: 45.0,
          0x4248: 50.0, 0x428C: 70.0, 0x42960000: None, 0x4346: 198.0, 0x435A: 218.0,
          0x42B4: 90.0, 0x42C8: 100.0, 0x42F0: 120.0}
hits2 = []
for off in range(0, SEC_SIZE, 4):
    w = struct.unpack_from('<I', seg, off)[0]
    if (w >> 26) != 0x0F:                     # lui
        continue
    rt, imm = (w >> 16) & 31, w & 0xFFFF
    if imm in FLOATS:
        hits2.append((SEC_ADDR + off, rt, imm))
# 按地址聚类 (窗口 0x60)
hits2.sort()
clusters, cur = [], []
for h in hits2:
    if cur and h[0] - cur[-1][0] > 0x60:
        clusters.append(cur); cur = []
    cur.append(h)
if cur:
    clusters.append(cur)
big = [c for c in clusters if len(c) >= 3]
print('   命中 %d 处; 聚成 %d 簇, 其中 >=3 个常量的簇 %d 个:'
      % (len(hits2), len(clusters), len(big)))
for c in big:
    print('   ── 0x%08X..0x%08X (%d 个常量)  %s'
          % (c[0][0], c[-1][0], len(c), fname(c[0][0])))
    for va, rt, imm in c:
        print('        %08X  lui %-6s 0x%04X  (= %.1f)' % (va, R[rt], imm, FLOATS[imm]))

print()
print('=' * 78)
print('C) 0x219A70 (DrawString v1) 附近的完整图标特判反汇编')
print('=' * 78)
import subprocess
print(subprocess.run([sys.executable, os.path.join(REPO, 'tools', 'diag', 'dis_ee.py'),
                      ELF, '0x219C00', '0xa0'], capture_output=True, text=True,
                     encoding='utf-8', errors='replace').stdout)
