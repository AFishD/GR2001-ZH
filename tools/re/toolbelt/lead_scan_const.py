# -*- coding: utf-8 -*-
r"""lead_scan_const.py — 扫 ELF 里所有 `addiu rd, zero, K` 立即数站点（用于核对常量唯一性）
用法: python lead_scan_const.py <iso> <K十进制> [iso0] [iso1]
默认扫描 SLUS_206.13 区段 (LBA295 .. GR.IMG 前)
"""
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
iso, K = sys.argv[1], int(sys.argv[2])
lo = int(sys.argv[3]) if len(sys.argv) > 3 else 295 * 2048
hi = int(sys.argv[4]) if len(sys.argv) > 4 else 19175 * 2048
BIAS = 0x6C780
data = open(iso, 'rb').read()
print('  扫描 ISO 0x%X..0x%X (%.1f MB) · 目标 addiu rd,zero,%d (0x%X)' % (lo, hi, (hi - lo) / 1e6, K, K))
hits = []
for off in range(lo, hi - 4, 4):
    w = struct.unpack_from('<I', data, off)[0]
    if (w >> 26) == 0x09 and ((w >> 21) & 0x1F) == 0 and ((w >> 16) & 0x1F) != 0 and (w & 0xFFFF) == K:
        hits.append((off, (w >> 16) & 0x1F))
print('  命中 %d 处:' % len(hits))
for off, rd in hits:
    print('    ISO 0x%08X = VA 0x%08X   addiu $%d, zero, %d   (word %s)'
          % (off, off + BIAS, rd, K, data[off:off + 4].hex()))
