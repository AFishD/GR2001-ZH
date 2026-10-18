# -*- coding: utf-8 -*-
r"""verify_iso_extend.py — 核验"用 ISO 目录记录扩大 MENU.IMG 声明长度"的精确上限

背景: 方案第①步 —— 把 MENU.IMG 的 data length 改大，让它吃到盘尾（ISO 总尺寸不变）。
      目录记录里 data length 有**小端 + 大端**两份（ISO9660 的规定），必须同时改。
本脚本: 读出 PVD / 根目录 / MENU.IMG 记录，算出**精确可扩展字节数**，并给出改动后的自洽性检查。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
SS = 2048
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

size = os.path.getsize(ISO)
f = open(ISO, 'rb')


def rd(lba, n):
    f.seek(lba * SS)
    return f.read(n)


pvd = rd(16, SS)
vol = struct.unpack_from('<I', pvd, 80)[0]
root = pvd[156:156 + 34]
root_lba = struct.unpack_from('<I', root, 2)[0]
root_len = struct.unpack_from('<I', root, 10)[0]

print('ISO 文件大小 %d B = %d 扇区' % (size, size // SS))
print('PVD vol_space = %d 扇区  ⇒ 两者 %s' % (vol, '一致 ✓' if vol == size // SS else '不一致 ✗'))
print('根目录 LBA=%d 长度=%d' % (root_lba, root_len))
print()

d = rd(root_lba, root_len)
i = 0
menu = None
while i < len(d):
    L = d[i]
    if L == 0:
        i += 1
        continue
    rec = d[i:i + L]
    nl = rec[32]
    name = rec[33:33 + nl].decode('ascii', 'replace')
    if name.upper().startswith('MENU'):
        menu = (i, L, rec, name)
    i += L

if not menu:
    print('✗ 没找到 MENU.IMG 记录')
    sys.exit(1)

off, L, rec, name = menu
abs_off = root_lba * SS + off
le = struct.unpack_from('<I', rec, 10)[0]
be = struct.unpack_from('>I', rec, 14)[0]
lba = struct.unpack_from('<I', rec, 2)[0]
lba_be = struct.unpack_from('>I', rec, 6)[0]
print('MENU.IMG 记录 @ISO 0x%X (根目录内偏移 0x%X, 长 %d)' % (abs_off, off, L))
print('  LBA  小端=%d 大端=%d  %s' % (lba, lba_be, '一致 ✓' if lba == lba_be else '不一致 ✗'))
print('  data length 小端 @0x%X = %d' % (abs_off + 10, le))
print('  data length 大端 @0x%X = %d  %s' % (abs_off + 14, be, '一致 ✓' if le == be else '不一致 ✗'))
print()

# 精确上限：从 MENU.IMG 的 LBA 到盘尾
max_sectors = vol - lba
max_bytes = max_sectors * SS
print('★ 精确上限:')
print('   从 MENU.IMG 的 LBA(%d) 到盘尾共 %d 扇区 = **%d B**' % (lba, max_sectors, max_bytes))
print('   现声明长度                     = %d B' % le)
print('   ⇒ **可扩展 %d B** (%.1f KB)' % (max_bytes - le, (max_bytes - le) / 1024))
print()
want = le + 30254
print('   空位任务主张可加 30,254 B ⇒ 新长度 %d B' % want)
print('   新长度需占 %d 扇区(向上取整) ; 允许 %d 扇区 ⇒ %s'
      % ((want + SS - 1) // SS, max_sectors, '**放得下 ✓**' if (want + SS - 1) // SS <= max_sectors else '**超出 ✗**'))
print()
print('★ 改动清单（两处必须同时改，ISO9660 规定）：')
print('   0x%X  (小端) %d → %d' % (abs_off + 10, le, want))
print('   0x%X  (大端) %d → %d' % (abs_off + 14, be, want))
print('   ⇒ 文件 LBA **不变**、ISO 总尺寸 **不变**、其它文件 **零位移** ✓')
print()
print('★ 注意: 盘尾 %d B 里最后会被新长度覆盖的部分 = %d B（其余仍为尾部填充）'
      % (max_bytes - le, 30254))
f.close()
