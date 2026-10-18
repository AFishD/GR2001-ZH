# -*- coding: utf-8 -*-
r"""iso_gaps.py — 解析 ISO9660 的 PVD + 根目录, 列出每个文件的 LBA/大小/间隙,
并定位 MENU.IMG 的目录记录（看它的 data length 字段能不能改）。

用法: python iso_gaps.py <iso路径>
"""
import io
import os
import struct
import sys

ISO = sys.argv[1] if len(sys.argv) > 1 else \
    r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization\work\builds\GR_ZH113b\GR_ZH113b.iso'
SS = 2048
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

f = open(ISO, 'rb')
size = os.path.getsize(ISO)
print('ISO %s' % ISO)
print('大小 %d B = %.1f MB = %d 扇区' % (size, size / 1e6, size // SS))
print()


def rd(lba, n):
    f.seek(lba * SS)
    return f.read(n)


# ---- PVD (LBA 16) ----
pvd = rd(16, SS)
print('PVD: type=%d id=%s  vol_space=%d 扇区' % (
    pvd[0], pvd[1:6].decode('ascii', 'replace'),
    struct.unpack_from('<I', pvd, 80)[0]))
root = pvd[156:156 + 34]
root_lba = struct.unpack_from('<I', root, 2)[0]
root_len = struct.unpack_from('<I', root, 10)[0]
print('根目录: LBA=%d 长度=%d' % (root_lba, root_len))
print()

# ---- 根目录条目 ----
ents = []
d = rd(root_lba, root_len)
i = 0
while i < len(d):
    L = d[i]
    if L == 0:
        i += 1
        continue
    rec = d[i:i + L]
    ext_lba = struct.unpack_from('<I', rec, 2)[0]
    ext_len = struct.unpack_from('<I', rec, 10)[0]
    flags = rec[25]
    nl = rec[32]
    name = rec[33:33 + nl].decode('ascii', 'replace')
    date = rec[18:25]
    ents.append((name, ext_lba, ext_len, L, i, date))
    i += L

print('=== 根目录条目（按 LBA 排序）===')
ents.sort(key=lambda e: e[1])
for name, lba, ln, rl, off, date in ents:
    print('  %-16s LBA %-8d 大小 %-12d 扇区 %-8d 目录记录长 %d @根目录偏移 0x%X' % (
        name, lba, ln, (ln + SS - 1) // SS, rl, off))
print()

print('=== 文件之间的空隙 ===')
end_prev = 0
tot_gap = 0
for name, lba, ln, rl, off, date in ents:
    gap = lba - end_prev
    if name not in ('.', '..'):
        tag = ''
        if gap > 0:
            tot_gap += gap * SS
            tag = '  ← 空隙 %d 扇区 = %d B' % (gap, gap * SS)
        print('  %-16s 起始 LBA %-8d (前一个文件结束于 %d)%s' % (name, lba, end_prev, tag))
    end_prev = lba + (ln + SS - 1) // SS
tail = size // SS - end_prev
print('  最后一个文件结束于 LBA %d ⇒ **盘尾尾部 %d 扇区 = %d B**' % (end_prev, tail, tail * SS))
print()
print('空隙合计 %d B ; 尾部 %d B ⇒ 可用连续空位合计 %d B' % (tot_gap, tail * SS, tot_gap + tail * SS))
print()

# ---- 定位 MENU.IMG 的目录记录里的 data length 字段 ----
for name, lba, ln, rl, off, date in ents:
    if name.upper().startswith('MENU'):
        abs_off = root_lba * SS + off
        print('=== %s 的目录记录（用于改 data length）===' % name)
        print('  记录位于 ISO 文件偏移 0x%X (LBA %d + 0x%X)' % (abs_off, root_lba, off))
        rec = rd(root_lba, root_len)[off:off + rl]
        print('  原字节: %s' % rec.hex())
        print('  data length 小端 @记录偏移 +10 = 0x%X: %d' % (
            abs_off + 10, struct.unpack_from('<I', rec, 10)[0]))
        print('  data length 大端 @记录偏移 +14 = 0x%X: %d' % (
            abs_off + 14, struct.unpack_from('>I', rec, 14)[0]))
        print('  ⇒ 若要让 MENU.IMG 变长, 改这两处（小端+大端各 4B）即可, LBA 不变 ✓')
        # 校验: 该记录的时间戳
        print('  记录时间: %04d-%02d-%02d %02d:%02d:%02d' % (1900 + date[0], date[1], date[2], date[3], date[4], date[5]))
