# -*- coding: utf-8 -*-
r"""zero_atlas4.py — 用**已实机验证过**的 tcslib 口径解图集（权威）

tcslib.atlas_container_segments / Atlas(patch_zh113_expand_font.py) 是 round67 写 329 字并
**实机显示正常**时用的解码，所以它是权威口径。本脚本用它重做普查。
"""
import json
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402
import numpy as np  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
base = 776286 * 2048
e3 = iso.img_entry(776286, 3)
pak = iso.read(base + e3['off'], e3['stored'])
q = 0
while q + 8 <= len(pak):
    mode, nl = struct.unpack_from('<II', pak, q)
    nm = pak[q + 8:q + 8 + nl].split(b'\x00')[0].decode('latin-1')
    r = q + 8 + nl
    psm, w, h, clut = struct.unpack_from('<IIII', pak, r)
    r2 = r + 16 + clut
    px = struct.unpack_from('<I', pak, r2)[0]
    if nm == 'new_font_revised':
        P0, PX, W, H = r2 + 4, px, w, h
        break
    q = r2 + 4 + px
print('px_off=0x%X px_size=0x%X w=%d h=%d' % (P0, PX, W, H))
blob = bytes(pak[P0:P0 + PX])
segs = tcslib.atlas_container_segments(blob, W // 2)
print('ATLAS_SEG_ROWS=%d ; 分段数 %d' % (tcslib.ATLAS_SEG_ROWS, len(segs) if segs else 0))
cov = 0
for k, (first_row, doff, nbytes) in enumerate(segs or []):
    nrow = nbytes // (W // 2)
    cov += nbytes
    print('  seg %-2d 首行 %-4d data_off 0x%-6X bytes 0x%-6X rows %d (行 %d..%d)'
          % (k, first_row, doff, nbytes, nrow, first_row, first_row + nrow - 1))
print('  段数据合计 %d / 像素总字节 %d (差 %d)' % (cov, W * H // 2, W * H // 2 - cov))

# 引擎口径图集
A = np.full((H, W), 1, dtype=np.uint8)
for first_row, doff, nbytes in segs:
    nrow = nbytes // (W // 2)
    if nrow == 0:
        continue
    PK = np.frombuffer(blob[doff:doff + nrow * (W // 2)], dtype=np.uint8).reshape(nrow, W // 2)
    sub = np.empty((nrow, W), dtype=np.uint8)
    sub[:, 0::2] = PK & 0x0F
    sub[:, 1::2] = (PK >> 4) & 0x0F
    A[first_row:first_row + nrow] = sub
    if nbytes % (W // 2):
        print('  (seg 首行 %d 尾部余 %d B 未纳入网格计算)' % (first_row, nbytes % (W // 2)))


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


print()
print('=== 引擎口径网格行普查 (h=%d) ===' % H)
blank = []
for r in range(0, 33):
    y = yrow(r)
    if y + 16 > H:
        print('  row %-2d y=%-4d 越界' % (r, y))
        continue
    cells = [(A[y:y + 16, 16 * c:16 * c + 16] == 0).sum() for c in range(62)]
    bl = [c for c, v in enumerate(cells) if v == 0]
    blank += [(r, c) for c in bl]
    print('  row %-2d y=%-4d 有墨 %2d/62 空白 %2d %s' % (r, y, 62 - len(bl), len(bl), bl[:14]))
print('  空白格合计 %d' % len(blank))

cs = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
zero = [s for s in range(1504)
        if not (A[yrow(s // 62):yrow(s // 62) + 16, 16 * (s % 62):16 * (s % 62) + 16] == 0).any()]
print()
print('★ 现役 1504 pair 格里"零墨"的 = %d  %s' % (len(zero), zero[:20]))
slot2ch = {(l - 0xA1) * 94 + (t - 0xA1): ch for ch, (l, t) in pair_of.items()}
print('  对应字符: %s' % [slot2ch.get(s) for s in zero[:20]])

print()
print('=== 带普查 ===')
for y0, y1, lab in ((194, 242, '图标跳空带'), (450, 498, '行25-27'), (498, 512, '底部'),
                    (0, 194, '行0-11'), (242, 450, '行12-24')):
    sub = A[y0:y1]
    i = int((sub == 0).sum())
    o = int(((sub != 0) & (sub != 1)).sum())
    print('  %-12s y[%d,%d) 面积 %-6d 墨 %-6d 杂散 %-4d 纯透明 %-6d (=%.1f 格)'
          % (lab, y0, y1, sub.size, i, o, sub.size - i - o, (sub.size - i - o) / 256.0))
np.save(os.path.join(OUT, 'atlas_engine_authoritative.npy'), A)
print()
print('[out] %s' % os.path.join(OUT, 'atlas_engine_authoritative.npy'))
iso.close()
