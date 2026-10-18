# -*- coding: utf-8 -*-
r"""gate_probe_b7.py — 只打 gate（4 字节 0xB1→0xB7）的 y≥512 判定探针

原理（无需改码位表）:
  打 gate 后，**单字节码 0xB4('用') 变成 lead** ⇒ 它会把下一个字节当 trail 吃掉
  ⇒ 该处渲染的格子 = slot (19×94 + (next−0xA1)) = 1786 + t ⇒ row = 1786/62 ≈ 28.8 ⇒ **row 28**
  ⇒ row 28 是**新行**（现役图集里 h=512 ⇒ 那里是 y≥498 的新区域）
  判据:
    ✅ 屏幕上原本是「用」的位置**变成乱码/别的图案** ⇒ 引擎**确实去采样了 row 28**
       ⇒ **y≥512 新行采样正常** ⇒ 全部扩容路线成立 ✓✓
    ❌ 屏幕**完全不变** ⇒ lead 未生效（gate 没打上或另有约束）⇒ 需查
    ❌ 直接崩 ⇒ 新行不可用
  基线对照: 同命令跑未打补丁的 GR_ZH113b（截图逐字节比较）
"""
import os
import shutil
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_TEST_GP_B7')
DST = os.path.join(OUTDIR, 'GR_TEST_GP_B7.iso')
SITES = [(0x416EE8, 0x3AA768), (0x417160, 0x3AA9E0), (0x41751C, 0x3AAD9C), (0x5656A4, 0x4F8F24)]
NEW_IMM = 0xB7
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.makedirs(OUTDIR, exist_ok=True)
if not os.path.exists(DST):
    print('  复制基底 1.53 GB …')
    shutil.copyfile(SRC, DST)

with open(DST, 'r+b') as f:
    for va, off in SITES:
        f.seek(off)
        w = struct.unpack('<I', f.read(4))[0]
        op, imm = w >> 26, w & 0xFFFF
        if op != 0x0B or imm != 0xB1:
            print('  ✗ 站点 0x%X 不符（op=0x%X imm=0x%X）⇒ 中止' % (va, op, imm))
            sys.exit(1)
        new = (w & 0xFFFF0000) | NEW_IMM
        f.seek(off)
        f.write(struct.pack('<I', new))
        print('  ✓ VA 0x%08X ISO 0x%08X: %08X → %08X' % (va, off, w, new))

# 逐字节差异核对（应恰好 4 个字节）
print('  逐字节核对 …')
diffs = []
CH = 1 << 22
with open(SRC, 'rb') as a, open(DST, 'rb') as b:
    pos = 0
    while True:
        ba, bb = a.read(CH), b.read(CH)
        if not ba:
            break
        if ba != bb:
            for i in range(min(len(ba), len(bb))):
                if ba[i] != bb[i]:
                    diffs.append(pos + i)
        pos += len(ba)
        if len(diffs) > 16:
            break
print('  差异字节: %d 个 ⇒ %s' % (len(diffs), ['0x%X' % d for d in diffs[:8]]))
print('  ⇒ %s' % ('✅ 恰好 4 字节，位置正确' if sorted(diffs) == sorted(o + 3 for _, o in SITES) else '⚠ 与预期不符'))
print('  盘: %s' % DST)
