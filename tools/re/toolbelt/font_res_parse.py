# -*- coding: utf-8 -*-
r"""font_res_parse.py — 解析 FONT.RES 的展开态结构，定位 face 记录与 W/H 字段

依据（反编译 RSFontMgr::ReadResourceFile @0x219380）:
  先读**一个字符串**（贴图名）→ 读 4 字节 face 数 → 每 face: 读名字串 + 若干 4 字节字段 →
  nrec = fld[4] × fld[5] → __nwa(nrec*10+0x10) → 每记录 1B,1B,2B,2B,2B,2B
本脚本: 用「字符串 + 4 字节字段」交替的模式扫描，找出 face 数与每个 face 的字段，并标出候选 W/H。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
R81 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

for fn in ('font_res_slot.bin', 'font_res_expanded.bin'):
    p = os.path.join(R81, fn)
    if not os.path.exists(p):
        print('  (缺 %s)' % fn)
        continue
    b = open(p, 'rb').read()
    print('=' * 78)
    print('%s  %d B' % (fn, len(b)))
    print('  头 64 字节: %s' % b[:64].hex())
    print('  u32[0..8]: %s' % [struct.unpack_from('<I', b, i * 4)[0] for i in range(9)])
    # 找所有可打印串（长度≥2，以 NUL 结尾）
    print('  字符串表:')
    i = 0
    while i < len(b) - 1:
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and b[j] != 0:
                j += 1
            if j - i >= 2 and j < len(b):
                print('    @0x%04X  %r   (长 %d, 后随 4B: %s)'
                      % (i, b[i:j].decode('latin-1'), j - i,
                         [struct.unpack_from('<I', b, j + 1 + k * 4)[0] for k in range(6)]
                         if j + 25 <= len(b) else '-'))
            i = j + 1
        else:
            i += 1
    print()
