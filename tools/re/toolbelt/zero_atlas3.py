# -*- coding: utf-8 -*-
r"""zero_atlas3.py — 用「图标窗 = 原版 8bpp 源的墨迹」这条**独立已知量**钉死像素起点偏移

gen_font16.py:124  ICON_BOX=(19,198,64,221) 且
    A[y0:y1, x0:x1] = ORIG8[y0:y1, x0:x1] != 31 ? INK : BG
其中 ORIG8 = COMMON_PAK.bin[0x146D : 0x146D+512*512] (原始 8bpp 面)
⇒ 用这条把 (头偏移, nibble 顺序) 一起解出来。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402
import numpy as np  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
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
        P0, PX = r2 + 4, px
        break
    q = r2 + 4 + px

ORIG_PAK = open(os.path.join(REPO, 'docs', 'han_v2', 'artifacts', 'COMMON_PAK.bin'), 'rb').read()
SURF = 0x146D
ORIG8 = np.frombuffer(ORIG_PAK[SURF:SURF + 512 * 512], dtype=np.uint8).reshape(512, 512)
TARGET = (ORIG8[198:221, 19:64] != 31)          # 布尔墨窗 23x45
print('图标窗目标: 墨点 %d / %d' % (int(TARGET.sum()), TARGET.size))
print('现役盘 COMMON.PAK 与 docs/han_v2/artifacts/COMMON_PAK.bin 同长? %s'
      % (len(pak) == len(ORIG_PAK)))


def build(off, order):
    raw = pak[P0 + off:P0 + off + 0x40000]
    PK = np.frombuffer(raw, dtype=np.uint8).reshape(512, 512)
    A = np.empty((512, 1024), dtype=np.uint8)
    if order == 'lo_even':
        A[:, 0::2] = PK & 0x0F
        A[:, 1::2] = (PK >> 4) & 0x0F
    else:
        A[:, 0::2] = (PK >> 4) & 0x0F
        A[:, 1::2] = PK & 0x0F
    return A


best = []
for off in range(0, 65):
    for order in ('lo_even', 'hi_even'):
        A = build(off, order)
        W = (A[198:221, 19:64] == 0)
        match = int((W == TARGET).sum())
        best.append((match, off, order))
best.sort(reverse=True)
print()
print('=== 图标窗匹配度 top8 (满分 %d) ===' % TARGET.size)
for m, off, order in best[:8]:
    print('  匹配 %-5d / %-5d  off=%-3d order=%s  (%.2f%%)'
          % (m, TARGET.size, off, order, 100.0 * m / TARGET.size))

m, OFF, ORDER = best[0]
A = build(OFF, ORDER)
print()
print('★ 钉死: 像素起点 = 容器 + %d ; nibble 顺序 = %s ; 匹配 %d/%d'
      % (OFF, ORDER, m, TARGET.size))
if ORDER == 'hi_even':
    print('  ⚠ 与 gen_font16 的 lo_even 约定相反 —— 需要复核')

PXD_abs = P0 + OFF
print('  绝对: ISO 0x%X (COMMON.PAK+0x%X)' % (base + PXD_abs, e3['off'] + PXD_abs))


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


print()
print('=== 校准后网格行普查 ===')
blank = []
for r in range(0, 28):
    y = yrow(r)
    cells = [(A[y:y + 16, 16 * c:16 * c + 16] == 0).sum() for c in range(62)]
    nz = sum(1 for v in cells if v)
    bl = [c for c, v in enumerate(cells) if v == 0]
    blank += [(r, c) for c in bl]
    print('  row %-2d y=%-4d 有墨 %2d/62 空白 %2d %s' % (r, y, nz, 62 - nz, bl))
print('  全部 28 行空白格合计 %d' % len(blank))

import json
cs = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
slot2ch = {}
for ch, (l, t) in pair_of.items():
    slot2ch[(l - 0xA1) * 94 + (t - 0xA1)] = ch
bad = [(row, col) for row, col in blank
       if (row * 62 + col) in slot2ch and slot2ch[row * 62 + col] not in ('',)]
print('  其中属于"现役 pair slot 但无墨"的 = %d' % len([1 for row, col in blank if row * 62 + col < 1504]))
print('  ★ 现役 1504 pair 格里零墨的 = %d' % sum(
    1 for s in range(1504) if not (A[yrow(s // 62):yrow(s // 62) + 16,
                                     16 * (s % 62):16 * (s % 62) + 16] == 0).any()))
np.save(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81', 'atlas_engine.npy'), A)
iso.close()
