# -*- coding: utf-8 -*-
r"""dump_font_record.py — 打印 COMMON.PAK 里 new_font_revised 记录的头部，定位 w/h/clut/px_size 字段

目的: 设计一个**真·单变量**探针 —— 只把该记录的 `h` 512→640（其余一律不动），
      看引擎是否接受 h=640（若界面文字仍与基底逐像素一致 ⇒ 接受 ✓；
      多出来的行会读到后续条目数据 ⇒ 无害，因为新行没有任何 UV 指向）。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286
iso = tcslib.Iso(ISO)

# 找 COMMON.PAK
pak = None
for i in range(20):
    e = iso.img_entry(MENU_LBA, i)
    if 'COMMON' in e['name'].upper():
        pak = e
        break
print('COMMON.PAK = MENU #%d off=0x%X stored=%d real=%d' % (i, pak['off'], pak['stored'], pak['real']))
raw = iso.read(pak['iso_off'], min(pak['real'], 0x20000))

# 记录起点: 由 common_pak_records.txt 得 0x1031（arrow 占 [0,0x1031)）
rec = 0x1031
print()
print('记录 @0x%X 起，头 96 字节:' % rec)
for k in range(0, 96, 16):
    seg = raw[rec + k:rec + k + 16]
    print('  +0x%03X  %s  %s' % (k, seg.hex(' '), ''.join(chr(c) if 32 <= c < 127 else '.' for c in seg)))
print()
print('按 u32 读（从记录起点起）:')
for k in range(0, 80, 4):
    v = struct.unpack_from('<I', raw, rec + k)[0]
    tag = ''
    if v == 1024:
        tag = '← ★ w = 1024'
    elif v == 512:
        tag = '← ★ h = 512（目标字段）'
    elif v == 0x410:
        tag = '← ★ clut_size = 0x410'
    elif v == 0x40010:
        tag = '← ★ px_size = 0x40010'
    elif v == 0x14:
        tag = '← psm = 0x14 (PSMT4)'
    print('  +0x%03X  %10d  0x%08X  %s' % (k, v, v, tag))
print()
print('⇒ 记下 h=512 与 w=1024 的精确偏移，供单变量探针使用 ✓')
iso.close()
