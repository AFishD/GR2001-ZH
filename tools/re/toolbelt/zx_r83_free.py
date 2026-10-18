# -*- coding: utf-8 -*-
r"""zx_r83_free.py — round83：原子图集 1024x512 的**自由度普查**（只读）

回答: 在不改 h(=512) 的前提下, 图集里还有多少 16x16 的"采样窗空间"可给新字用?

口径（全部来自盘上实测, 不靠假设）:
  · 对偶码格位  = tcslib.atlas_cell_xy_engine_view(slot)  → 16x16
  · 记录采样窗  = (u0+4, v0+2) .. (u1+4, v1+2)   [GLYPH_DU/GLYPH_DV]
产出 work/builds/GR_ZH98/temp/r83/free.txt
"""
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np     # noqa: E402
import tcslib          # noqa: E402
import zx_lib          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
os.makedirs(OUT, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MENU_LBA = tcslib.MENU_LBA
W, H = 1024, 512
DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV
B = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    B.append(s)


iso = tcslib.Iso(ISO)
names = []
for i in range(2000):
    e = iso.img_entry(MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])

# --- 容器解出引擎图 ---
pak_e = iso.img_entry(MENU_LBA, names.index('COMMON.PAK'))
pak = bytes(iso.read(pak_e['iso_off'], pak_e['stored']))
recs = tcslib.parse_pak_records(pak)
R = recs[1]
cont = pak[R[6]:R[6] + R[5]]
img, cov = zx_lib.decode_engine(cont, W, H)
P('容器 %d B ; 引擎图覆盖行 %.2f%%' % (len(cont), 100.0 * cov.sum() / (W * H)))
P('图集墨 texel = %d / %d' % (int(img.sum()), W * H))

# --- 面记录 ---
ft_e = iso.img_entry(MENU_LBA, names.index('FONT.RES'))
slot = bytes(iso.read(ft_e['iso_off'], ft_e['stored']))
exp = b''.join(s[0] for s in tcslib.lzo_subs(slot))
he, faces = tcslib.parse_ft_faces(exp)
P('FONT.RES 展开 %d B ; 记录区结束 0x%X' % (len(exp), he))

# --- 占用图 ---
occ_grid = np.zeros((H, W), dtype=bool)      # 对偶码格位
occ_rec = np.zeros((H, W), dtype=bool)       # 记录采样窗 (三个 face 全部)
rec_list = []
for (nm, fld, rs) in faces:
    for r_i, r in enumerate(rs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        rec_list.append((nm, r_i, b0, b1, u0, v0, u1, v1))
        x0, y0, x1, y1 = u0 + DU, v0 + DV, u1 + DU, v1 + DV
        x0c, y0c = max(0, x0), max(0, y0)
        x1c, y1c = min(W, x1), min(H, y1)
        if x1c > x0c and y1c > y0c:
            occ_rec[y0c:y1c, x0c:x1c] = True
P('非空记录 %d 条 (三面合计)' % len(rec_list))

LEAD_LO, LEAD_HI = tcslib.LEAD_LO, tcslib.LEAD_HI
P('tcslib LEAD_LO=0x%X LEAD_HI=0x%X PAIR_LEAD_HI=0x%X pair_capacity=%d'
  % (LEAD_LO, LEAD_HI, tcslib.PAIR_LEAD_HI, tcslib.pair_capacity()))
used_slots = tcslib.pair_capacity()
maxrow = -1
for s in range(used_slots):
    x, y = tcslib.atlas_cell_xy_engine_view(s)
    row = s // tcslib.NCOL
    maxrow = max(maxrow, row)
    x1, y1 = min(W, x + 16), min(H, y + 16)
    if x1 > x and y1 > y:
        occ_grid[y:y1, x:x1] = True
P('现役对偶 slot 0..%d (row 0..%d) ; 格位覆盖墨区' % (used_slots - 1, maxrow))
P('格位占用 texel = %d ; 记录占用 texel = %d ; 并集 = %d'
  % (int(occ_grid.sum()), int(occ_rec.sum()), int((occ_grid | occ_rec).sum())))
P('格位 ∩ 记录 = %d texel  (重叠 ⇒ 记录与格位共用区域)' % int((occ_grid & occ_rec).sum()))

# --- 16x16 网格上的空闲度 ---
P('')
P('--- 以 16x16 为单位 (x=16k, y=16m) 的占用表 (G=格位 R=记录 B=both .=空) ---')
free_cells = []
for m in range(H // 16):
    line = []
    for k in range(W // 16):
        sl = (slice(16 * m, 16 * m + 16), slice(16 * k, 16 * k + 16))
        g, r = occ_grid[sl].any(), occ_rec[sl].any()
        line.append('B' if (g and r) else 'G' if g else 'R' if r else '.')
        if not (g or r):
            free_cells.append((k, m))
    P('  y=%3d m=%2d  %s' % (16 * m, m, ''.join(line)))
P('★ 完全空闲的 16x16 网格单元 = %d 个: %s' % (len(free_cells), free_cells))

# --- 任意位置的空闲 16x16 窗 (滑窗) ---
P('')
P('--- 滑窗: (x,y) 处 16x16 完全空闲的位置数 (x 0..1008, y 0..496) ---')
busy = occ_grid | occ_rec
cnt = 0
spots = []
for y in range(0, H - 15):
    for x in range(0, W - 15):
        if not busy[y:y + 16, x:x + 16].any():
            cnt += 1
            if x % 16 == 0 and y % 16 == 0:
                spots.append((x, y))
P('  任意 (x,y) 位置数 = %d' % cnt)
P('  其中 16 对齐的位置 %d 个' % len(spots))
# 最大连通空闲区
try:
    from scipy import ndimage                                        # noqa: F401
    HAVE_SCIPY = True
except Exception:                                                    # noqa: BLE001
    HAVE_SCIPY = False
P('  scipy 可用 = %s' % HAVE_SCIPY)

# --- 逐行/逐列空闲带 ---
P('')
P('--- 逐行: 该行 16 行带内完全无占用的 x 区间 ---')
for m in range(H // 16):
    rowsl = slice(16 * m, 16 * m + 16)
    g = occ_grid[rowsl].any(axis=0)
    r = occ_rec[rowsl].any(axis=0)
    b = g | r
    # 找连续空闲 x 段
    segs = []
    i = 0
    while i < W:
        if not b[i]:
            j = i
            while j < W and not b[j]:
                j += 1
            segs.append((i, j, j - i))
            i = j
        else:
            i += 1
    segs = [s for s in segs if s[2] >= 16]
    P('  m=%2d y=%3d 格位占用列数 %4d 记录占用列数 %4d ⇒ 空闲 x 段(>=16px) %s'
      % (m, 16 * m, int(g.sum()), int(r.sum()), segs))

# --- 记录采样窗的 y 带分布 ---
P('')
P('--- 记录采样窗 y 带分布 ---')
bands = {}
for (nm, r_i, b0, b1, u0, v0, u1, v1) in rec_list:
    bands.setdefault((v0 + DV, v1 + DV), []).append((nm, r_i, u0 + DU, u1 + DU))
for k in sorted(bands):
    xs = sorted({(a, b) for (_, _, a, b) in bands[k]})
    P('  v带 %s : %d 条 ; x 范围 %d..%d ; 唯一 x 段 %d 个'
      % (k, len(bands[k]), min(a for a, _ in xs), max(b for _, b in xs), len(xs)))

# --- 图标码记录 (480,213)-(490,229) 的采样窗内有墨吗 ---
P('')
P('--- "图标/空白" 记录 (480,213)-(490,229) 采样窗 (484,215)-(494,231) 的墨量 ---')
w = img[215:231, 484:494]
P('    墨 texel = %d / %d' % (int(w.sum()), w.size))
P('--- 记录 (0,195)-(16,211) 采样窗 (4,197)-(20,213) 的墨量 ---')
w2 = img[197:213, 4:20]
P('    墨 texel = %d / %d' % (int(w2.sum()), w2.size))
for (nm, r_i, b0, b1, u0, v0, u1, v1) in rec_list:
    if (u0, v0, u1, v1) in ((480, 213, 490, 229), (0, 195, 16, 211), (384, 213, 400, 229),
                            (416, 213, 432, 229), (448, 213, 464, 229), (320, 213, 336, 229),
                            (352, 213, 368, 229)):
        ww = img[v0 + DV:v1 + DV, u0 + DU:u1 + DU]
        P('    face %-8s idx %3d rect=%s 采样窗=%s 墨=%d/%d'
          % (nm, r_i, (u0, v0, u1, v1), (u0 + DU, v0 + DV, u1 + DU, v1 + DV),
             int(ww.sum()), ww.size))

iso.close()
with open(os.path.join(OUT, 'free.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'free.txt'))
