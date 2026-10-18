# -*- coding: utf-8 -*-
r"""diff_font_record_fields.py — 对比两个盘上 new_font_revised 记录的头 96 字节，
找出"随 px_size 变化而应当更新、但补丁可能没更新"的派生字段

背景: 引擎按块读纹理容器（历史记录: B' = 0x40000/W, vpackets=497(W=512),
      +0x30 = px_size − 16·ceil(px_size/(B'+16))）⇒ 记录里可能有**派生字段**。
      若补丁只改 h/px_size 而未同步它 ⇒ 块读错位 ⇒ 卡死（实测 0 截图/0 纹理上传）。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

MENU_LBA = 776286
REC = 0x1031      # new_font_revised 记录起点（容器内偏移）

def load(path):
    iso = tcslib.Iso(os.path.join(REPO, path))
    for i in range(20):
        e = iso.img_entry(MENU_LBA, i)
        if 'COMMON' in e['name'].upper():
            raw = iso.read(e['iso_off'], e['stored'])
            iso.close()
            return raw
    iso.close()
    return None

a = load('work/builds/GR_ZH113b/GR_ZH113b.iso')
b = load('work/builds/GR_ZH121/GR_ZH121.iso')
print('原盘 PAK %d B · 成品 PAK %d B' % (len(a), len(b)))
print()
print('记录头 96 字节逐 u32 对比（rec=0x%X）:' % REC)
print('  off   原盘        成品        差异')
for k in range(0, 96, 4):
    va = struct.unpack_from('<I', a, REC + k)[0]
    vb = struct.unpack_from('<I', b, REC + k)[0]
    mark = '' if va == vb else '   ← ★ 变了'
    print('  +0x%03X %10d  %10d%s' % (k, va, vb, mark))
print()
print('⇒ 关键: 若某个**由 px_size 派生**的字段（如块数/块长）没变，就会卡死 ✗')
print('   已知容器: 原 262,160 B = 8 段×0x8000 ；成品 328,176 B = 10 段×0x8000 + 16')
print('   历史公式: Bp = 0x40000/W = 0x100 (W=1024); vpackets = 0x40000/Bp, 见历史报告')
print('   +0x030 的历史公式: px_size - 16*ceil(px_size/(Bp+16))')
