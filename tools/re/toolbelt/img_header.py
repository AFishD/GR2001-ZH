# -*- coding: utf-8 -*-
r"""img_header.py — 定位 IMG 容器头里的"条目数"字段（加新条目的前置）

已知: GR.IMG 4070 条 / MENU.IMG 686 条（用 tcslib.img_entry 逐条解析得到）。
做法: 在容器头 0x1000 字节内搜所有等于条目数的 u32/u16/u8, 打印偏移与上下文,
      并核对"表末尾"(0x830 + 48*n) 与"名字区"边界, 确认字段位置不冲突。
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

for label, lba, count in (('GR.IMG', 19175, 4070), ('MENU.IMG', 776286, 686)):
    base = lba * 2048
    hdr = iso.read(base, 0x1000)
    print('=' * 78)
    print('%s @LBA %d  条目数 = %d' % (label, lba, count))
    print('  头 64 字节: %s' % hdr[:64].hex())
    print('  u32[0..12]: %s' % [struct.unpack_from('<I', hdr, i * 4)[0] for i in range(12)])
    # 搜 u32/u16 等于 count 的位置
    hits32 = [i for i in range(0, 0x1000 - 4, 4)
              if struct.unpack_from('<I', hdr, i)[0] == count]
    hits16 = [i for i in range(0, 0x1000 - 2, 2)
              if struct.unpack_from('<H', hdr, i)[0] == count]
    print('  **u32 == %d 的位置: %s**' % (count, ['0x%X' % h for h in hits32]))
    print('   u16 == %d 的位置: %s' % (count, ['0x%X' % h for h in hits16[:8]]))
    # 相关边界
    tbl_end = 0x830 + 48 * count
    noff = struct.unpack_from('<I', hdr, 0x10)[0]
    nend = struct.unpack_from('<I', hdr, 0x04)[0]
    print('  推算表末尾 0x%X ; 头里字段@0x10 = 0x%X ; 头里字段@0x04 = 0x%X' % (tbl_end, noff, nend))
    for h in hits32:
        print('     ★ 字段 @0x%X = %d   (与表末尾相差 %d，与名字区起点相差 %d)'
              % (h, count, h - tbl_end, h - noff))
    print()

iso.close()
