# -*- coding: utf-8 -*-
r"""p1p_patch_h.py — P1′ 探针: 只把 COMMON.PAK 里 new_font_revised 记录的 h 512→640

真·单变量: 除这 4 个字节外，全盘逐字节与 GR_ZH113b 相同。
依据: 记录 @pak+0x1031 ; h 在记录 +0x020 ; COMMON.PAK @MENU.IMG off 0x57400
      ⇒ ISO 绝对偏移 = 0x57400 + 0x1031 + 0x020 = 0x58451
"""
import os
import shutil
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_TEST_P1P_H640')
DST = os.path.join(OUTDIR, 'GR_TEST_P1P_H640.iso')
MENU_LBA = 776286
MENU_BASE = MENU_LBA * 2048          # ★ 必须加上 MENU.IMG 在 ISO 里的基址
PAK_OFF = 0x57400
REC_OFF = 0x1031
H_FIELD = 0x020
OFF = MENU_BASE + PAK_OFF + REC_OFF + H_FIELD
NEW_H = 640
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

os.makedirs(OUTDIR, exist_ok=True)
if not os.path.exists(DST):
    print('  复制基底 1.53 GB …')
    shutil.copyfile(SRC, DST)
    print('  完成')

with open(DST, 'r+b') as f:
    f.seek(OFF)
    before = struct.unpack('<I', f.read(4))[0]
    print('  补丁前 h @0x%X = %d' % (OFF, before))
    if before != 512:
        print('  ✗ 期望 512，实际 %d ⇒ 偏移可能不对，中止' % before)
        sys.exit(1)
    f.seek(OFF)
    f.write(struct.pack('<I', NEW_H))
    f.seek(OFF)
    after = struct.unpack('<I', f.read(4))[0]
    print('  补丁后 h @0x%X = %d' % (OFF, after))

# 逐字节差异核对（只允许 1 处 4 字节差异）
print('  逐字节核对（只应差这一处）…')
CH = 1 << 22
diff_blocks = []
with open(SRC, 'rb') as a, open(DST, 'rb') as b:
    pos = 0
    while True:
        ba = a.read(CH)
        bb = b.read(CH)
        if not ba:
            break
        if ba != bb:
            n = min(len(ba), len(bb))
            for i in range(n):
                if ba[i] != bb[i]:
                    diff_blocks.append(pos + i)
                    if len(diff_blocks) > 16:
                        break
        pos += len(ba)
        if len(diff_blocks) > 16:
            break
print('  差异字节数: %d  位置: %s' % (len(diff_blocks), ['0x%X' % d for d in diff_blocks[:8]]))
ok = len(diff_blocks) == 4 and all(0x58451 <= d < 0x58455 for d in diff_blocks)
print('  ⇒ %s' % ('✅ 真·单变量（只差 h 那 4 字节）' if ok else '⚠ 差异超出预期，请检查'))
print('  盘: %s' % DST)
