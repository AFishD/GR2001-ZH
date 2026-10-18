# -*- coding: utf-8 -*-
r"""meta_patch_test.py — 元测试: 打一个**必然可见**的补丁，验证"我的 ISO 补丁到底有没有生效"

做法: 把 4 处 gate 的立即数从 0xB1 改成 **0x01**
  ⇒ 按反汇编规则，字节 ∈ [0xA1, 0x00] 为空集 ⇒ **所有对偶码都会退化成"单字节"**
  ⇒ 屏幕上所有汉字（对偶编码）必成乱码/错字 ⇒ **必然可见** ✓
判据:
  ✅ 文字大面积异常 ⇒ **补丁管线有效** ⇒ 之前的"零变化"是真实行为（须另找解释）
  ❌ 文字完全正常   ⇒ **补丁管线有问题**（补丁没被引擎读到）⇒ 先修管线，别再做别的探针
"""
import os
import shutil
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_TEST_META01')
DST = os.path.join(OUTDIR, 'GR_TEST_META01.iso')
SITES = [(0x416EE8, 0x3AA768), (0x417160, 0x3AA9E0), (0x41751C, 0x3AAD9C), (0x5656A4, 0x4F8F24)]
NEW_IMM = 0x01
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.makedirs(OUTDIR, exist_ok=True)
if not os.path.exists(DST):
    print('  复制基底 …')
    shutil.copyfile(SRC, DST)

with open(DST, 'r+b') as f:
    for va, off in SITES:
        f.seek(off)
        w = struct.unpack('<I', f.read(4))[0]
        op, imm = w >> 26, w & 0xFFFF
        if op != 0x0B or imm not in (0xB1, 0xB7):
            print('  ✗ 站点 0x%X 不符（op=0x%X imm=0x%X）⇒ 中止' % (va, op, imm))
            sys.exit(1)
        new = (w & 0xFFFF0000) | NEW_IMM
        f.seek(off)
        f.write(struct.pack('<I', new))
        print('  ✓ VA 0x%08X ISO 0x%08X: %08X → %08X (立即数 0x%X → 0x01)'
              % (va, off, w, new, imm))

diffs = []
with open(SRC, 'rb') as a, open(DST, 'rb') as b:
    pos = 0
    CH = 1 << 22
    while True:
        ba, bb = a.read(CH), b.read(CH)
        if not ba:
            break
        if ba != bb:
            for i in range(min(len(ba), len(bb))):
                if ba[i] != bb[i]:
                    diffs.append(pos + i)
        pos += len(ba)
print('  差异字节 %d 个 ⇒ %s' % (len(diffs), ['0x%X' % d for d in diffs[:8]]))
print('  盘: %s' % DST)
