# -*- coding: utf-8 -*-
r"""_dbg_ascii_band.py — 量化「ASCII 字形表被网格格位覆盖」的范围与可修复空间（只读）

    python tools/re/toolbelt/_dbg_ascii_band.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                     # noqa: E402
import fa_recon as R                                                   # noqa: E402

B = lambda *a: os.path.join(REPO, 'work', 'builds', *a)
F = R.read_font(B('GR_FA2400', 'GR_FA2400.iso'))
w, h = F['w'], F['h']
# 网格采样区: 64 列 ⇒ x = 16*col 全覆盖; 行 y = 2+16*(row+3*[row>=12])
grid = np.zeros((h, w), dtype=bool)
for row in range(37):
    y = 2 + 16 * (row + (3 if row >= 12 else 0))
    grid[y:y + 16, :] = True
print('图集 %dx%d ; 网格采样行覆盖 y=%s' % (w, h, sorted(set(np.where(grid[:, 0])[0]))))

# 逐 face 统计"记录矩形落在网格采样区"的条数与面积
for (nm, fld, rows) in F['faces']:
    hit = []
    for i, (_o, r) in enumerate(rows):
        u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
        if u1 <= u0 or v1 <= v0:
            continue
        if grid[v0:min(v1, h), u0:min(u1, w)].any():
            hit.append((i, i + 0x20, u0, v0, u1, v1))
    print('face %-8s 非空记录 %d ; 与网格采样区相交 %d 条'
          % (nm, sum(1 for (_o, r) in rows if r[4] > r[2]), len(hit)))
    if hit:
        print('   前 8 条:', hit[:8])
        xs = sorted(set((u0, u1) for (_i, _c, u0, _v0, u1, _v1) in hit))
        print('   涉及 x 区间 %d 种: %s' % (len(xs), xs[:8]))
        ys = sorted(set((v0, v1) for (_i, _c, _u0, v0, _u1, v1) in hit))
        print('   涉及 y 区间 %d 种: %s' % (len(ys), ys[:8]))
# 跳过带 (y=194..241) 的记录占用情况
band = (194, 241)
occ = np.zeros((band[1] - band[0], w), dtype=bool)
n_band = 0
for (nm, fld, rows) in F['faces']:
    for (_o, r) in rows:
        u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
        if u1 <= u0 or v1 <= v0:
            continue
        if v0 >= band[0] and v1 <= band[1]:
            occ[v0 - band[0]:v1 - band[0], u0:u1] = True
            n_band += 1
print('跳过带 y=%d..%d 内记录 %d 条 ; 占用 texel %d / %d (%.1f%%)'
      % (band[0], band[1], n_band, int(occ.sum()), occ.size, 100.0 * occ.mean()))
# 每行剩余空白
for y in range(0, band[1] - band[0], 16):
    row = occ[y]
    free = (~row).sum()
    # 找连续空白段 (>=64 px)
    runs, cur = [], None
    for x in range(w):
        if not row[x] and cur is None:
            cur = x
        elif row[x] and cur is not None:
            if x - cur >= 64:
                runs.append((cur, x))
            cur = None
    if cur is not None and w - cur >= 64:
        runs.append((cur, w))
    print('   y=%3d 空 %4d px ; ≥64px 空白段: %s' % (band[0] + y, free, runs[:6]))
