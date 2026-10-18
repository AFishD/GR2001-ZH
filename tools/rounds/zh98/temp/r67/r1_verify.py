# -*- coding: utf-8 -*-
r"""r1_verify.py — round67 第 1 步: **独立**复核「329 空闲格 + 51 条过期标注」这个前提。

口径 (与 p7/p8 同源, 但这里自己重算一遍, 不引用它们的结论):
  · 引擎格坐标 = tcslib.atlas_cell_xy_engine_view(slot)  (= 16*col, yrow(row))  ← 无相位
  · 墨 = 图集引擎视图 texel == 0
  · 记录矩形 = FONT.RES **全部 3 个 face** 的记录 (u0,v0,u1,v1) 覆盖
  · 空闲 = 零墨 且 无记录矩形 且 在贴图内
额外做两件事:
  A) 反向校验坐标系 —— 现役 1175 个已用 slot 的引擎格应当**全部有墨** (否则口径错了);
  B) 把 51 条 ATLAS_ENGINE_SINGLE_CELLS 标注逐条按像素判定, 列出来。
"""
import json
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

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH111', 'GR_ZH111.iso')
OUT = HERE

f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
print('[atlas] %s psm=0x%02X %dx%d px_off=0x%X px_size=0x%X'
      % (atlas['name'], atlas['psm'], W, H, atlas['px_off'], atlas['px_size']))
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
ink = gray == 0

rect = np.zeros((H, W), dtype=bool)
owner = {}
for (nm, fld, recs) in faces:
    nz = 0
    for i, r in enumerate(recs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 > u0 and v1 > v0:
            nz += 1
            rect[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True
            owner.setdefault((nm, i), []).append((u0, v0, u1, v1))
    print('[FT] face=%-8s nrec=%d 非空记录=%d fld[1]=%d fld[4]x[5]=%dx%d'
          % (nm, len(recs), nz, fld[1], fld[4], fld[5]))

cs = tcslib.Charset()
used = {tcslib.pair_slot(*p): ch for ch, p in cs.enc_pair.items()}
print('[charset] 对偶 %d 单字节 %d; slot %d..%d'
      % (len(used), len(cs.enc_single), min(used), max(used)))

# ---------- A) 反向校验坐标系 ----------
bad_used = [(s, used[s]) for s in sorted(used)
            if not ink[tcslib.atlas_cell_xy_engine_view(s)[1]:
                       tcslib.atlas_cell_xy_engine_view(s)[1] + 16,
                       tcslib.atlas_cell_xy_engine_view(s)[0]:
                       tcslib.atlas_cell_xy_engine_view(s)[0] + 16].any()]
print('\n[A] 现役 %d 个已用 slot 中, 引擎格零墨的 = %d  %s'
      % (len(used), len(bad_used), bad_used[:10] if bad_used else ''))
# 对照: 用 legacy 口径 (4+16*col) 数墨, 应当明显更差
bad_legacy = 0
for s in used:
    x, y = tcslib.atlas_cell_xy(s)
    if not ink[y:y + 16, x:x + 16].any():
        bad_legacy += 1
print('[A] 对照 legacy 口径 (4+16*col) 零墨 = %d/%d  ⇒ 引擎口径胜出 %d 个'
      % (bad_legacy, len(used), bad_legacy - len(bad_used)))

# ---------- B) 51 条标注逐条判定 ----------
print('\n[B] ATLAS_ENGINE_SINGLE_CELLS 逐条按**当前像素**判定 (共 %d 条):'
      % len(tcslib.ATLAS_ENGINE_SINGLE_CELLS))
stale, live = [], []
for (row, col), note in sorted(tcslib.ATLAS_ENGINE_SINGLE_CELLS.items()):
    slot = row * tcslib.NCOL + col
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    c = int(ink[y:y + 16, x:x + 16].sum())
    r = int(rect[y:y + 16, x:x + 16].sum())
    rec = (c == 0 and r == 0)
    (stale if rec else live).append((row, col, slot, x, y, c, r, note))
    print('   row=%2d col=%2d slot=%4d (%4d,%3d) 墨=%3d 记录压=%3d  %s   [%s]'
          % (row, col, slot, x, y, c, r, note, '过期' if rec else '仍成立'))
print('   ⇒ 过期 %d 条 / 仍成立 %d 条' % (len(stale), len(live)))

# ---------- C) 逐格账本 ----------
def audit(lead_hi_excl, name):
    free, usedn, ink_n, rec_n, oob = [], 0, [], [], []
    for lead in range(0xA1, lead_hi_excl):
        for trail in range(0xA1, 0xFF):
            slot = tcslib.pair_slot(lead, trail)
            if slot in used:
                usedn += 1
                continue
            x, y = tcslib.atlas_cell_xy_engine_view(slot)
            if x + 16 > W or y + 16 > H:
                oob.append(slot)
                continue
            c = int(ink[y:y + 16, x:x + 16].sum())
            r = int(rect[y:y + 16, x:x + 16].sum())
            if c:
                ink_n.append((slot, c))
            elif r:
                rec_n.append((slot, r))
            else:
                free.append(slot)
    print('\n[C] %s: lead 0xA1..0x%02X 可寻址 slot %d | 已用 %d | ★空闲 %d | 有墨 %d | 记录压 %d | 越界 %d'
          % (name, lead_hi_excl - 1, (lead_hi_excl - 0xA1) * 94, usedn, len(free), len(ink_n),
             len(rec_n), len(oob)))
    return free

free_b = audit(0xAE, '假说B lead<=0xAD')
free_now = audit(0xB1, '现役 gate lead<=0xB0')
audit(0xB4, '假说A lead<=0xB3')

# ---------- D) 空闲格分布 + 边界断言 ----------
print('\n[D] 现役 gate 口径下空闲 %d 格:' % len(free_now))
from collections import Counter                                                 # noqa: E402
lc = Counter(tcslib.pair_from_slot(s)[0] for s in free_now)
for lead in sorted(lc):
    sl = sorted(s for s in free_now if tcslib.pair_from_slot(s)[0] == lead)
    tr = [tcslib.pair_from_slot(s)[1] for s in sl]
    print('   lead 0x%02X: %3d 格  slot %4d..%4d  trail 0x%02X..0x%02X'
          % (lead, lc[lead], sl[0], sl[-1], min(tr), max(tr)))
print('   合计 %d; 与 1175 相加 = %d (引擎容量 %d)'
      % (len(free_now), 1175 + len(free_now), tcslib.pair_capacity()))

mx = 0
for s in free_now:
    x, y = tcslib.atlas_cell_xy_engine_view(s)
    assert x + 16 <= W and y + 16 <= H, (s, x, y)
    mx = max(mx, x + 16)
print('   ★全部 %d 格在贴图内; 右缘最大 x+16 = %d (< %d); 底缘最大 y+16 = %d (< %d)'
      % (len(free_now), mx, W,
         max(tcslib.atlas_cell_xy_engine_view(s)[1] + 16 for s in free_now), H))
assert mx < W, mx
# 目标格互不重叠 (同行相邻 col 差 1 ⇒ x 差 16, 天然不重叠; 这里实测确认)
cells = {}
overlap = 0
for s in free_now:
    x, y = tcslib.atlas_cell_xy_engine_view(s)
    key = (x, y)
    if key in cells:
        overlap += 1
    cells[key] = s
print('   ★空闲格坐标唯一性: 重复 %d 个 (0 = 没有两个 slot 抢同一格)' % overlap)
assert overlap == 0

json.dump(dict(iso=ISO, free_slots=sorted(free_now), n_free=len(free_now),
               stale_notes=[list(t[:7]) + [t[7]] for t in stale],
               live_notes=[list(t[:7]) + [t[7]] for t in live],
               used_zero_ink=bad_used, used_zero_ink_legacy=bad_legacy),
          open(os.path.join(OUT, 'r1_verify.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n[OUT] %s' % os.path.join(OUT, 'r1_verify.json'))
