# -*- coding: utf-8 -*-
r"""zero_atlas.py — 逐 texel 量现役图集：墨/透明/杂散，以及各"死区"到底有多少可放字的面

只读 GR_ZH113b.iso 的 COMMON.PAK 记录 new_font_revised。
输出 work/builds/GR_ZH98/temp/r81/atlas_census.txt
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402
import numpy as np  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
LS = []


def say(s=''):
    print(s)
    LS.append(s)


MENU_LBA = 776286
base = MENU_LBA * 2048
e3 = iso.img_entry(MENU_LBA, 3)
pak = iso.read(base + e3['off'], e3['stored'])
assert e3['name'] == 'COMMON.PAK'
# record #1
q = 0
recs = []
while q + 8 <= len(pak):
    mode, nl = struct.unpack_from('<II', pak, q)
    nm = pak[q + 8:q + 8 + nl].split(b'\x00')[0].decode('latin-1')
    r = q + 8 + nl
    psm, w, h, clut = struct.unpack_from('<IIII', pak, r)
    r2 = r + 16 + clut
    px = struct.unpack_from('<I', pak, r2)[0]
    recs.append(dict(off=q, name=nm, mode=mode, psm=psm, w=w, h=h, clut=clut, px=px,
                     px_off=r2 + 4, end=r2 + 4 + px))
    q = r2 + 4 + px
font = [r for r in recs if r['name'] == 'new_font_revised'][0]
say('COMMON.PAK 记录 %s' % [(r['name'], hex(r['off']), hex(r['end'])) for r in recs])
say('new_font_revised: psm=0x%02X w=%d h=%d clut=0x%X px_size=0x%X 像素数据 @pak+0x%X'
    % (font['psm'], font['w'], font['h'], font['clut'], font['px'], font['px_off']))

blob = pak[font['px_off']:font['px_off'] + font['px']]
say('像素容器 %d B; 前 96 字节:' % len(blob))
for k in range(0, 96, 16):
    say('   +0x%04X  %s' % (k, blob[k:k + 16].hex(' ')))
# 找所有 GIF tag (低 16 位 NREG=0,EOP=1, 高 16 位 = NLOOP)
tags = []
for k in range(0, len(blob) - 16, 16):
    v = struct.unpack_from('<Q', blob, k)[0]
    nloop = (v >> 16) & 0x7FFF
    eop = (v >> 15) & 1
    nreg = (v >> 28) & 0xF
    if nreg == 0 and eop == 1 and 0 < nloop <= 0x4000:
        tags.append((k, nloop, eop, v & 0xFFFF))
say('疑似 GIFTAG (16B 对齐, NREG=0 EOP=1) %d 个:' % len(tags))
for k, nloop, eop, lo in tags[:20]:
    say('   @0x%-6X NLOOP=0x%X (%d) lo=0x%04X' % (k, nloop, nloop, lo))

PXD = font['px_off']
PK = np.frombuffer(pak[PXD:PXD + 0x40000], dtype=np.uint8).reshape(512, 512)
A = np.empty((512, 1024), dtype=np.uint8)
A[:, 0::2] = PK & 0x0F
A[:, 1::2] = (PK >> 4) & 0x0F
say('')
say('=== texel 统计 (1024x512) ===')
vals, cnts = np.unique(A, return_counts=True)
for v, c in zip(vals.tolist(), cnts.tolist()):
    say('  nibble 0x%X : %d texel' % (v, c))
ink = (A == 0)
say('  墨(0x0) %d ; 非墨 %d' % (int(ink.sum()), int((~ink).sum())))
# 16x16 网格格 (与 ELF 公式一致) 逐格是否有墨
def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


say('')
say('=== 网格格 (x=16*col, y=yrow(row)) 每行墨格数 ===')
for r in range(0, 33):
    y = yrow(r)
    if y + 16 > 512:
        say('  row %-2d y=%-4d 越界' % (r, y))
        continue
    cells = []
    for c in range(62):
        sub = A[y:y + 16, 16 * c:16 * c + 16]
        cells.append(int((sub == 0).sum()))
    nz = sum(1 for v in cells if v)
    say('  row %-2d y=%-4d 有墨格 %2d/62 ; 空白格 %2d ; 满格(>=64墨点) %2d'
        % (r, y, nz, 62 - nz, sum(1 for v in cells if v >= 64)))

say('')
say('=== 各自由带的面积 (texel) ===')
def band(y0, y1, x0=0, x1=1024, label=''):
    sub = A[y0:y1, x0:x1]
    tot = sub.size
    i = int((sub == 0).sum())
    o = int(((sub != 0) & (sub != 1)).sum())
    say('  %-28s y[%d,%d) x[%d,%d)  面积 %-7d 墨 %-7d 杂散 %-6d 纯透明 %-7d (=%.1f 格)'
        % (label, y0, y1, x0, x1, tot, i, o, tot - i - o, (tot - i - o) / 256.0))
    return tot - i - o


free_bands = 0
free_bands += band(194, 242, 0, 1024, '图标跳空带 y194-242')
free_bands += band(450, 498, 0, 1024, '行25-27带 y450-498')
free_bands += band(498, 512, 0, 1024, '底部 y498-512')
free_bands += band(0, 512, 0, 20, '左缘 x0-20')
free_bands += band(0, 512, 992, 1024, '右缘 x992-1024')
say('  —— 自由带合计纯透明 %d texel = %.1f 格(256 texel)' % (free_bands, free_bands / 256.0))

# 精确: 每个 16x16 格 (任意 16 对齐位置) 是否纯透明
say('')
say('=== 全图 16x16 对齐格的"纯透明"计数 (含 x0=16c, y=任意16倍数) ===')
tot_free = 0
for y in range(0, 512, 16):
    row_free = []
    for c in range(64):
        if 16 * c + 16 > 1024:
            break
        sub = A[y:y + 16, 16 * c:16 * c + 16]
        if not (sub == 0).any():
            row_free.append(c)
    tot_free += len(row_free)
say('  16 对齐格中"无墨"的 = %d (总 32x64=2048)' % tot_free)

# 有墨格 vs 网格格 的关系
say('')
say('=== 现役 1504 个 pair 格 + 110 单字节格的墨量复核（坐标系反证）===')
import json
cs = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
bad = 0
for ch, (l, t) in pair_of.items():
    slot = (l - 0xA1) * 94 + (t - 0xA1)
    row, col = slot // 62, slot % 62
    y = yrow(row)
    sub = A[y:y + 16, 16 * col:16 * col + 16]
    if not (sub == 0).any():
        bad += 1
say('  1504 个 pair 格里"零墨"的 = %d （应为 0）' % bad)

open(os.path.join(OUT, 'atlas_census.txt'), 'w', encoding='utf-8').write('\n'.join(LS) + '\n')
iso.close()
print('\n[OUT] %s' % os.path.join(OUT, 'atlas_census.txt'))
