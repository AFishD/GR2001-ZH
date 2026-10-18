# -*- coding: utf-8 -*-
r"""check_5657e0.py — 核对各盘在 VA 0x5657E0 处是否带着那条 1 指令修复
映射（上一轮实测更正）: ISO = VA - 0x6C780  =>  VA 0x5657E0 => ISO 0x4F9060
修复前该字 = 0x95050002 (lhu a1,2(t0)) ; 修复后 = 0x95050000 (lhu a1,0(t0))
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
VA = 0x5657E0
OFF = VA - 0x6C780

CANDS = [
    'work/builds/GR_ZH113b/GR_ZH113b.iso',
    'work/builds/GR_ZH119/GR_ZH119.iso',
    'work/builds/GR_ZH123/GR_ZH123.iso',
    'work/builds/GR_ZH124/GR_ZH124.iso',
    'work/builds/GR_F364/GR_F364.iso',
]
print('VA 0x%08X -> ISO 0x%08X' % (VA, OFF))
print()
for rel in CANDS:
    p = os.path.join(REPO, rel)
    if not os.path.exists(p):
        print('  %-44s (缺)' % os.path.basename(rel))
        continue
    with open(p, 'rb') as f:
        f.seek(OFF)
        w = struct.unpack('<I', f.read(4))[0]
    tag = 'FIXED(0x95050000)' if w == 0x95050000 else ('BUGGY(0x95050002)' if w == 0x95050002 else '???')
    print('  %-30s %08X  %s' % (os.path.basename(rel), w, tag))
print()
print('  参考: 同族 gate 站点 VA 0x5656A4 => ISO 0x4F8F24 （F364 差异窗口里有它 ✓）')
