# -*- coding: utf-8 -*-
r"""parse_bdv2.py — 解析 PCSX2 block dump (BDV2): 16B 头 + N*(u32 LBA + 2048B data)
用途: 从用户崩溃那次运行里取出**读盘序列**，看它停在哪、以及崩前在读什么
"""
import collections
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
p = REPO + r'\work\builds\GR_ZH113b\GR_ZH113b (2026-10-15 19-39-44).dump'
data = open(p, 'rb').read()
sig, bs, nsec, x = struct.unpack_from('<4I', data, 0)
print('  头: %r block=%d total_sectors=%d u4=%d  file=%d B' % (sig.to_bytes(4, 'little'), bs, nsec, x, len(data)))
stride = 4 + bs
n = (len(data) - 16) // stride
print('  记录数 = %d (余 %d B)' % (n, (len(data) - 16) - n * stride))
lbas = [struct.unpack_from('<I', data, 16 + i * stride)[0] for i in range(n)]
print('  最大 LBA = %d · 不同扇区数 = %d' % (max(lbas), len(set(lbas))))
print('  前 20 次读: %s' % lbas[:20])
print('  后 60 次读: %s' % lbas[-60:])


def region(l):
    if l < 16:
        return 'sys(<16)'
    if l < 19175:
        return 'iso-dir/other'
    if l < 776286:
        return 'GR.IMG'
    if l < 804768:
        return 'MENU.IMG'
    return 'beyond-volume'


c = collections.Counter(region(l) for l in lbas)
print('  区域分布: %s' % dict(c))
# MENU.IMG 内的细分：PAK 区 / 新 FONT.RES 区 / 其他
pak0, pak1 = 776460, 776720
fn0 = 776784
menu = [l for l in lbas if 776286 <= l < 804768]
print('  MENU.IMG 段: %d 次 · 其中 PAK 区(%d..%d) %d 次 · >=%d(新 FONT.RES 起) %d 次 · 其余 %d 次'
      % (len(menu), pak0, pak1, sum(1 for l in menu if pak0 <= l <= pak1),
         fn0, sum(1 for l in menu if l >= fn0), sum(1 for l in menu if l < pak0)))
# 末尾 300 次读里 MENU.IMG 的分布（看是否卡在某个文件上反复读）
tail = lbas[-300:]
print('  末 300 次读的区域: %s' % dict(collections.Counter(region(l) for l in tail)))
print('  末 300 次读里 LBA>=776286 的最小/最大: %s / %s'
      % (min([l for l in tail if l >= 776286], default=None), max(tail)))
