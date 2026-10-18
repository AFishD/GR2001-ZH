# -*- coding: utf-8 -*-
r"""p8_blocked.py — 现役盘上 slot 1175..1503 里"不可用"的那 51 个, **逐格**查清为什么。

关键疑点: `tcslib.ATLAS_ENGINE_SINGLE_CELLS` 里"行 19 col 0..33 / 行 24 col 0..5,12"
是 round45 的标注 —— 而 round55 已把那批单字节记录**搬到 y=195/211 带**了。
若那些格子现在其实**零墨且无记录矩形**, 标注就是过期的, 容量要重算。
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                     # noqa: E402
import tcslib                                                             # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
ink = gray == 0
rect = np.zeros((H, W), dtype=bool)
owner = {}
for (nm, _fld, recs) in faces:
    for i, r in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 > u0 and v1 > v0:
            rect[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True

cs = tcslib.Charset()
used = set(tcslib.pair_slot(*p) for p in cs.enc_pair.values())

print('== slot 1175..1503 里被判"不可用"的格子, 逐格查因 ==')
kinds = {}
for slot in range(1175, 1504):
    if slot in used:
        continue
    row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    c = int(ink[y:y + 16, x:x + 16].sum())
    r = int(rect[y:y + 16, x:x + 16].sum())
    conf = tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((row, col))
    if c == 0 and r == 0 and not conf:
        continue
    why = []
    if c:
        why.append('墨%d' % c)
    if r:
        why.append('记录压%d' % r)
    if conf:
        why.append('标注:%s' % conf)
    key = ' + '.join(why)
    kinds.setdefault(key, []).append((slot, row, col, x, y, c, r))
    print('  slot=%4d row=%2d col=%2d (%4d,%3d)  %s' % (slot, row, col, x, y, key))

print('\n== 归类 ==')
for k in sorted(kinds, key=lambda z: -len(kinds[z])):
    lst = kinds[k]
    print('  %-46s %3d 个  slot %s' % (k, len(lst),
                                       '%d..%d' % (lst[0][0], lst[-1][0]) if len(lst) > 4
                                       else ' '.join(str(t[0]) for t in lst)))

print('\n== ATLAS_ENGINE_SINGLE_CELLS 标注 vs 实际 ==')
stale = []
for (row, col), note in sorted(tcslib.ATLAS_ENGINE_SINGLE_CELLS.items()):
    x, y = tcslib.atlas_cell_xy_engine_view(row * tcslib.NCOL + col)
    c = int(ink[y:y + 16, x:x + 16].sum())
    r = int(rect[y:y + 16, x:x + 16].sum())
    if c == 0 and r == 0:
        stale.append((row, col, note))
print('  标注总数 %d；其中**现在其实零墨且无记录矩形**的 = %d 个'
      % (len(tcslib.ATLAS_ENGINE_SINGLE_CELLS), len(stale)))
print('  %s' % (stale[:40] if stale else '（无 —— 标注全部仍然成立的）'))

print('\n== 结论数字 ==')
n_clean = 0
n_clean_with_conf = 0
for slot in range(1175, 1504):
    if slot in used:
        continue
    row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    c = int(ink[y:y + 16, x:x + 16].sum())
    r = int(rect[y:y + 16, x:x + 16].sum())
    conf = tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((row, col))
    if c == 0 and r == 0:
        n_clean_with_conf += 1
        if not conf:
            n_clean += 1
print('  slot 1175..1503 = %d 个; 已用 %d 个'
      % (1504 - 1175, len([s for s in range(1175, 1504) if s in used])))
print('  **物理干净**(零墨 + 无记录矩形) = %d 个  (其中被过期标注挡住 %d 个)'
      % (n_clean_with_conf, n_clean_with_conf - n_clean))
print('  ⇒ 按"实际像素"口径还能加 %d 个汉字; 按 tcslib 标注口径 %d 个'
      % (n_clean_with_conf, n_clean))
