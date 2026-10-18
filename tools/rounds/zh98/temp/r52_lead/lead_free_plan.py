# -*- coding: utf-8 -*-
r"""lead_free_plan.py — 侦察: 那 88 个"被活字形占着"的格子, 到底能不能腾出来? 怎么腾?

核心思路: 单字节字形只由 **FT 记录矩形**定位 ⇒ 只要把字形**搬到对偶网格之外**的空区
(引擎的 62x25 对偶网格永不采样那里), 再改记录指向新位置 ⇒
  · 字形照常显示 (引擎按记录采样)
  · 那 88 个对偶格**空出来**变成可用格
  · 净增 88 个可用格 (234 -> 322)

本脚本回答:
  ① 88 个格子分别被哪条记录占着? 每条记录占几个格?
  ② 每个格是否被**恰好一条**记录覆盖 (多条的搬不动/要特别处理)?
  ③ 对偶网格之外有多少**干净空区**可以放字形? (跳过的 3 行 + 回绕列)
  ④ FONT.RES 记录表在哪、怎么改
"""
import io
import json
import os
import sys
from collections import Counter

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH103', 'GR_ZH103.iso')
w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128
cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
code2ch = {int(v): k for k, v in cs['codes'].items()}

rec = [r for f, _x, rs in faces if f == 'large' for r in rs]
rect_of = {}
for idx, r in enumerate(rec):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 > u0 and v1 > v0:
        rect_of[idx + 0x20] = (u0, v0, u1, v1)
live_code = set(c for c in rect_of
                if c in (0x7B, 0x7D, 0xB1, 0xB5) or 0x20 <= c <= 0x7E
                or (c in code2ch))
live_mask = np.zeros((H, W), dtype=bool)
for c in live_code:
    u0, v0, u1, v1 = rect_of[c]
    live_mask[v0:v1, u0:u1] = True

slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        slot_of[tcslib.pair_slot(b1, b2)] = ch

# ── ① 每个"被活字形占着"的格子: 归属 ────────────────────────────────
print('=' * 78)
print('① 88 个"被活字形占着"的格子: 归属哪条记录')
print('=' * 78)
own = {}
for slot in range(1504):
    if slot in slot_of:
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        continue
    cell = ink[y:y + 16, x:x + 16]
    if not cell.any():
        continue
    held = int((cell & live_mask[y:y + 16, x:x + 16]).sum())
    if held != int(cell.sum()):
        continue
    owners = [c for c in live_code
              if x < rect_of[c][2] and x + 16 > rect_of[c][0]
              and y < rect_of[c][3] and y + 16 > rect_of[c][1]]
    own[slot] = owners
multi = {s: o for s, o in own.items() if len(o) > 1}
print('  格子 %d 个; 其中被**多条**记录覆盖的 %d 个' % (len(own), len(multi)))
print('  被 1 条覆盖的: %d 个' % (len(own) - len(multi)))
cnt = Counter()
for s, o in own.items():
    for c in o:
        cnt[c] += 1
print()
print('  按记录统计 (一条记录占几个格子):')
for c, n in sorted(cnt.items(), key=lambda kv: -kv[1]):
    u0, v0, u1, v1 = rect_of[c]
    nm = code2ch.get(c) or (chr(c) if 0x20 <= c < 0x7F else '')
    print('    0x%02X %-3s rec=(%4d,%3d,%4d,%4d) %2d 格' % (c, nm, u0, v0, u1, v1, n))
print()
print('  被多条覆盖的格子 (搬字时要一起处理):')
for s, o in sorted(multi.items())[:20]:
    x, y = tcslib.atlas_cell_xy_engine_view(s)
    print('    slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d) 记录: %s'
          % (s, s // 62, s % 62, x, y, ' '.join('0x%02X' % c for c in o)))

# ── ③ 对偶网格之外的干净空区 ────────────────────────────────────────
print()
print('=' * 78)
print('③ 对偶网格之外的空区 (可以放搬走的字形)')
print('=' * 78)
used_mask = np.zeros((H, W), dtype=bool)
for s in slot_of:
    x, y = tcslib.atlas_cell_xy_engine_view(s)
    used_mask[y:y + 16, x:x + 16] = True
ftmask = np.zeros((H, W), dtype=bool)
for c, (u0, v0, u1, v1) in rect_of.items():
    ftmask[v0:v1, u0:u1] = True

# 网格行占用的 y 区间
grid_y = set()
for row in range(25):
    y = 2 + 16 * (row + 3 * (row >= 12))
    for yy in range(y, y + 16):
        grid_y.add(yy)
free_rows = [y for y in range(H) if y not in grid_y]
print('  对偶网格占用的 y 行数 %d ; 空出的 y 行数 %d' % (len(grid_y), len(free_rows)))
# 找连续空行段
runs, start = [], None
for y in range(H):
    if y in grid_y:
        if start is not None:
            runs.append((start, y - 1)); start = None
    else:
        if start is None:
            start = y
if start is not None:
    runs.append((start, H - 1))
print('  连续空行段:')
for a, b in runs:
    blk = ink[a:b + 1, :]
    # 该段里"既不在网格槽位、也不在任何记录矩形"的干净 16x16 格数
    clean = 0
    for y0 in range(a, b - 15 + 1, 16):
        for x0 in range(0, W - 15, 16):
            if not blk[y0 - a:y0 - a + 16, x0:x0 + 16].any() and not ftmask[y0:y0 + 16, x0:x0 + 16].any():
                clean += 1
    print('    y=%3d..%3d (%2d 行) 墨 %5d px ; 干净 16x16 格 %d 个'
          % (a, b, b - a + 1, int(blk.sum()), clean))
# 回绕列 x=992..1023
wrap = ink[:, 992:1024]
print('  回绕列 x=992..1023: 墨 %d px' % int(wrap.sum()))
print()
print('⇒ 搬走 88 个字形需要 88 个干净 16x16 格 (每格 256 px)')
