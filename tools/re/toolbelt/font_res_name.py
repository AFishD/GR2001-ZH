# -*- coding: utf-8 -*-
r"""font_res_name.py — 定位 FONT.RES 里的"贴图名字符串"（方案第 4 步的编辑点）

依据(反编译): RSFontMgr::ReadResourceFile 先读**一个字符串**存进 mgr+0x1c —— 那就是贴图名。
本案贴图名应为 new_font_revised.rsb（旧报告: GetTexture(ui_text_mgr, mgr+0x1c)）。
本脚本: 在 MENU.IMG 里找出 FONT.RES 条目, 解析它的头部, 打印第一个字符串与前后结构。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)

# 1) 在 MENU.IMG 里找 FONT.RES
LBA = 776286
n = 0
target = None
while n < 2000:
    try:
        e = iso.img_entry(LBA, n)
    except Exception:
        break
    if e['name'].startswith('?'):
        break
    if 'FONT' in e['name'].upper():
        target = e
        print('找到条目 #%d  %s  off=0x%X stored=%d real=%d' % (n, e['name'], e['off'], e['stored'], e['real']))
        break
    n += 1
if not target:
    print('✗ 没找到 FONT.RES')
    sys.exit(1)

raw = iso.read(target['iso_off'], target['stored'])
print('  前 96 字节: %s' % raw[:96].hex())
print('  可打印视图: %s' % ''.join(chr(c) if 32 <= c < 127 else '.' for c in raw[:96]))

# 2) 解析: 第一个字段按 u32 读, 然后是一个字符串
cnt = struct.unpack_from('<I', raw, 0)[0]
print('  u32[0] = %d   (反编译里 face 数是从流里读的 4 字节)' % cnt)
# 在头 256 字节里找可打印串
import re
for m in re.finditer(rb'[ -~]{4,}', raw[:512]):
    s = m.group().decode('latin-1')
    print('  字符串 @0x%X: %r' % (m.start(), s))
print()
print('=== 结论 ===')
print('  FONT.RES 容器条目: %s @MENU.IMG off=0x%X (ISO 偏移 0x%X) stored=%d'
      % (target['name'], target['off'], target['iso_off'], target['stored']))
iso.close()
