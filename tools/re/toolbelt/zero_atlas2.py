# -*- coding: utf-8 -*-
r"""zero_atlas2.py — 校准图集像素起点 + 正确的自由格普查

上一步的发现: 许多网格行恰好"2 个空白格" ⇒ 疑似像素流被 16 字节 (32 texel = 2 格) 平移过。
本脚本扫描 0..64 字节的头偏移, 取"行 0..24 每行有墨格数最多"的那个 offset。
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
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
base = 776286 * 2048
e3 = iso.img_entry(776286, 3)
pak = iso.read(base + e3['off'], e3['stored'])
q = 0
recs = []
while q + 8 <= len(pak):
    mode, nl = struct.unpack_from('<II', pak, q)
    nm = pak[q + 8:q + 8 + nl].split(b'\x00')[0].decode('latin-1')
    r = q + 8 + nl
    psm, w, h, clut = struct.unpack_from('<IIII', pak, r)
    r2 = r + 16 + clut
    px = struct.unpack_from('<I', pak, r2)[0]
    recs.append(dict(name=nm, off=q, psm=psm, w=w, h=h, clut=clut, px=px, px_off=r2 + 4, end=r2 + 4 + px))
    q = r2 + 4 + px
font = [r for r in recs if r['name'] == 'new_font_revised'][0]
P0 = font['px_off']
PX = font['px']
print('像素容器长度 0x%X (= 0x40000 + %d)' % (PX, PX - 0x40000))
print('容器前 48 字节: %s' % pak[P0:P0 + 48].hex(' '))
print('尾部 32 字节  : %s' % pak[P0 + PX - 32:P0 + PX].hex(' '))


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


def decode(off):
    raw = pak[P0 + off:P0 + off + 0x40000]
    PK = np.frombuffer(raw, dtype=np.uint8).reshape(512, 512)
    A = np.empty((512, 1024), dtype=np.uint8)
    A[:, 0::2] = PK & 0x0F
    A[:, 1::2] = (PK >> 4) & 0x0F
    return A


best = None
print()
print('=== 头偏移扫描: 行 0..24 每行有墨格数 ===')
for off in range(0, 65, 4):
    A = decode(off)
    tot = 0
    per = []
    for r in range(25):
        y = yrow(r)
        n = sum(1 for c in range(62) if (A[y:y + 16, 16 * c:16 * c + 16] == 0).any())
        per.append(n)
        tot += n
    print('  off=%-3d 合计有墨格 %-4d  %s' % (off, tot, ' '.join('%2d' % n for n in per[:14])))
    if best is None or tot > best[1]:
        best = (off, tot)
print('  ★ 最佳偏移 = %d (有墨格合计 %d)' % best)

OFF = best[0]
A = decode(OFF)
ink0 = A
print()
print('=== 校准后 (off=%d) 网格行墨格普查 ===' % OFF)
for r in range(0, 33):
    y = yrow(r)
    if y + 16 > 512:
        print('  row %-2d y=%-4d 越界 (>512)' % (r, y))
        continue
    cells = [(A[y:y + 16, 16 * c:16 * c + 16] == 0).sum() for c in range(62)]
    nz = sum(1 for v in cells if v)
    print('  row %-2d y=%-4d 有墨格 %2d/62 ; 空白 %2d ; 满格 %2d'
          % (r, y, nz, 62 - nz, sum(1 for v in cells if v >= 64)))

print()
print('=== 校准后 texel/nibble 统计 ===')
vals, cnts = np.unique(A, return_counts=True)
for v, c in zip(vals.tolist(), cnts.tolist()):
    print('  nibble 0x%X : %d' % (v, c))
ink = (A == 0)
print('  墨 %d ; 非墨 %d ; 纯透明(1) %d ; 杂散 %d'
      % (int(ink.sum()), int((~ink).sum()), int((A == 1).sum()), int(((A != 0) & (A != 1)).sum())))


def band(y0, y1, label):
    sub = A[y0:y1, :]
    i = int((sub == 0).sum())
    o = int(((sub != 0) & (sub != 1)).sum())
    tot = sub.size
    print('  %-22s y[%d,%d) 面积 %-6d 墨 %-6d 杂散 %-5d 纯透明 %-6d (=%.1f 格)'
          % (label, y0, y1, tot, i, o, tot - i - o, (tot - i - o) / 256.0))


print()
print('=== 校准后各带 ===')
band(194, 242, '图标跳空带')
band(242, 450, '网格行12-24')
band(450, 498, '行25-27')
band(498, 512, '底部14px')
band(0, 194, '网格行0-11')

# 现役 1504 pair 格反证
cs = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
bad = 0
for ch, (l, t) in pair_of.items():
    slot = (l - 0xA1) * 94 + (t - 0xA1)
    row, col = slot // 62, slot % 62
    y = yrow(row)
    if not (A[y:y + 16, 16 * col:16 * col + 16] == 0).any():
        bad += 1
print()
print('★ 校准后: 1504 个现役 pair 格里"零墨"的 = %d （0 = 坐标系与偏移都对）' % bad)
np.save(os.path.join(OUT, 'atlas_engine.npy'), A)
iso.close()
