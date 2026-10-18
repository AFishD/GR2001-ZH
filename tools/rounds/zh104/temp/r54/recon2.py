# -*- coding: utf-8 -*-
r"""recon2.py — 搬运前第二侦察: **格子级**重叠 (相位/回绕列) + 目标布局试算。

为什么还要查:
  · `atlas_cell_xy_engine_view` 对**回绕列**会 y+1 ⇒ 网格行 11 的回绕格覆盖 y=179..194,
    即 **y=194 那一条也属于在用格** ⇒ 新矩形不能落在 y=194;
  · 旧矩形 (尤其 0xB2 那种 16x16 的) 可能压在**同一行回绕格**上 ⇒ 清它就会打到在用格。

本脚本:
  ① 旧 84 矩形 pixel-level 与"在用对偶格"的交集 (= 待清像素里有没有在用格的像素);
  ② 试算布局: 84 条 = 80 个 16x16 + 4 个小矩形 (5x13 / 7x13), 每个独占一个 16x16 格,
     全部落在 y=195..226 (2 条 16 行带, 避开 y=194 回绕行与 y=242 行 12);
  ③ 校验: 新矩形互不重叠 / 不与任何 face 任何记录矩形重叠 / 不与在用对偶格重叠 /
     完全在 y=194..241 内;
  ④ 打印最终搬运表 (旧矩形 → 新矩形)。
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                        # noqa: E402
import tcslib                                                # noqa: E402
from patch_zh94_glyph_align import Atlas                     # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH103', 'GR_ZH103.iso')
CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}

w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
A = Atlas(bytearray(ad['pak']), ad['px_off'], ad['px_size'])
ink = A.eng
cs = json.load(io.open(CHARSET, encoding='utf-8'))
code2ch = {int(v): k for k, v in cs['codes'].items()}

face_rect = {}
for nm, fld, rs in faces:
    face_rect[nm] = {}
    for i, r in enumerate(rs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 > u0 and v1 > v0:
            face_rect[nm][i + 0x20] = (u0, v0, u1, v1)

# ---- 搬运源 = recon.py 的 84 条 ----
REC = json.load(io.open(os.path.join(HERE, 'recon.json'), encoding='utf-8'))
src = {m['code']: (tuple(m['rect']), m['w'], m['h']) for m in REC['moves']}
print('搬运源 %d 条' % len(src))

# ---- 布局: 2 条 16 行带 y=195..210 / 211..226, x = 16*k ----
BAND_Y = (195, 211)
CELLS = [(y0, 16 * k) for y0 in BAND_Y for k in range(64)]
print('可用新格 %d 个 (y=%s, x=0..1008 步 16)' % (len(CELLS), '/'.join(map(str, BAND_Y))))
assert len(CELLS) >= len(src)

# 小矩形先排 (它们在带尾, 免得和 16x16 的挤在一起也没关系 —— 一律每格一条)
small = [c for c in src if src[c][1] != 16 or src[c][2] != 16]
big = [c for c in src if c not in small]
order = sorted(big) + sorted(small)
moves = {}
for c, (y0, x0) in zip(order, CELLS):
    (_r, ww, hh) = src[c]
    moves[c] = (x0, y0, x0 + ww, y0 + hh)
assert len(moves) == len(src)

# ---- 校验 ----
newmask = np.zeros((H, W), dtype=bool)
FREE = (194, 242)
for c, (u0, v0, u1, v1) in moves.items():
    assert FREE[0] <= v0 and v1 <= FREE[1], ('新矩形越界', c, v0, v1)
    assert not newmask[v0:v1, u0:u1].any(), ('新矩形互相重叠', c)
    newmask[v0:v1, u0:u1] = True

# 与所有 face 的所有记录矩形重叠?
n_ov = 0
for nm, rs in face_rect.items():
    for c, (u0, v0, u1, v1) in rs.items():
        if c in moves:
            continue
        if newmask[v0:v1, u0:u1].any():
            n_ov += 1
            print('  !! 新矩形与 %s 0x%02X %s 重叠' % (nm, c, (u0, v0, u1, v1)))
assert n_ov == 0, n_ov
print('① 新矩形: 互不重叠 ✓, 与其它记录矩形重叠 0 ✓, 全在 y=%d..%d ✓'
      % (FREE[0], FREE[1] - 1))

# 与在用对偶格重叠?
slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        slot_of[tcslib.pair_slot(b1, b2)] = ch
used_mask = np.zeros((H, W), dtype=bool)
for s in slot_of:
    x, y = tcslib.atlas_cell_xy_engine_view(s)
    if 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H:
        used_mask[y:y + 16, x:x + 16] = True
print('② 在用对偶格 %d 个; 新矩形 ∩ 在用格 = %d px (必须 0)'
      % (len(slot_of), int((newmask & used_mask).sum())))
assert not (newmask & used_mask).any()

# ---- ③ 旧 84 矩形 ∩ 在用格 (清它会不会打到在用格?) ----
print()
print('=' * 78)
print('③ 旧矩形 pixel-level 与在用格的交集 (待清像素里有没有在用格的像素)')
print('=' * 78)
bad = []
tot = 0
for c, (r, ww, hh) in sorted(src.items()):
    u0, v0, u1, v1 = r
    m = np.zeros((H, W), dtype=bool)
    m[v0:v1, u0:u1] = True
    ov = m & used_mask
    n = int(ov.sum())
    if n:
        slots = [s for s in slot_of
                 if not (tcslib.atlas_cell_xy_engine_view(s)[0] + 16 <= u0
                         or tcslib.atlas_cell_xy_engine_view(s)[0] >= u1
                         or tcslib.atlas_cell_xy_engine_view(s)[1] + 16 <= v0
                         or tcslib.atlas_cell_xy_engine_view(s)[1] >= v1)]
        inkn = int((ov & ink).sum())
        bad.append((c, r, n, inkn, [(s, slot_of[s], tcslib.atlas_cell_xy_engine_view(s))
                                    for s in slots]))
        tot += n
for c, r, n, inkn, slots in bad:
    print('  0x%02X %s ∩ 在用格 %d px (其中有墨 %d px): %s'
          % (c, r, n, inkn, ' '.join('%s@slot%d%s' % (ch, s, xy) for s, ch, xy in slots)))
print('  合计: %d 条旧矩形压到在用格, 交集 %d px' % (len(bad), tot))

# ---- ④ 最终搬运表 ----
print()
print('=' * 78)
print('④ 搬运表 (84 条: 旧矩形 → 新矩形)')
print('=' * 78)
rows = []
for c in sorted(src):
    (u0, v0, u1, v1), ww, hh = src[c]
    nu0, nv0, nu1, nv1 = moves[c]
    assert (nu1 - nu0, nv1 - nv0) == (ww, hh)
    ch = code2ch.get(c) or {0x7B: '{', 0x7D: '}', 0xE7: 'ç', 0xF1: 'ñ'}.get(c, '?')
    npx = int(ink[v0:v1, u0:u1].sum())
    assert int(ink[nv0:nv1, nu0:nu1].sum()) == 0, ('新矩形非空', c)
    rows.append(dict(code=c, char=ch, old=[u0, v0, u1, v1], new=[nu0, nv0, nu1, nv1],
                     w=ww, h=hh, ink=npx))
    print('    0x%02X %-3s (%4d,%3d,%4d,%4d) → (%4d,%3d,%4d,%4d)  %2dx%-2d 墨 %3d'
          % (c, ch, u0, v0, u1, v1, nu0, nv0, nu1, nv1, ww, hh, npx))
print('  合计 %d 条, 待搬墨 %d px' % (len(rows), sum(r['ink'] for r in rows)))

out = dict(layout=dict(bands=list(BAND_Y), x_step=16, n_cells=len(CELLS)),
           old_rect_vs_used=[[c, list(r), n, inkn,
                              [[s, ch, list(xy)] for s, ch, xy in slots]]
                             for c, r, n, inkn, slots in bad],
           moves=rows)
io.open(os.path.join(HERE, 'layout.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print()
print('[rep] → %s' % os.path.join(HERE, 'layout.json'))
