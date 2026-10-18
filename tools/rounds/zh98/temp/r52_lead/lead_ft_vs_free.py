# -*- coding: utf-8 -*-
r"""lead_ft_vs_free.py — ★ 关键冲突检查: FT 记录矩形 vs **可用格**(空白槽位)

用户指出: 空格(0x20)的记录矩形压在 4 个"可用格"上 —— 往那些格写新字会不会出事?
本脚本对**全部** FT 记录矩形 × 全部槽位状态做交叉检查, 并给出"真正安全的可用格"数。
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

slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        slot_of[tcslib.pair_slot(b1, b2)] = ch

# 槽位状态 (与 font_cell_map 一致: used / free_blank / held_ft / recyclable)
live_code = set()
for c in rect_of:
    if c in (0x7B, 0x7D, 0xB1, 0xB5) or 0x20 <= c <= 0x7E or c in code2ch:
        live_code.add(c)
live_mask = np.zeros((H, W), dtype=bool)
for c in live_code:
    u0, v0, u1, v1 = rect_of[c]
    live_mask[v0:v1, u0:u1] = True

status = {}
for slot in range(1504):
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        status[slot] = 'unaddressable'; continue
    cell = ink[y:y + 16, x:x + 16]
    if slot in slot_of:
        status[slot] = 'used'
    elif not cell.any():
        status[slot] = 'free_blank'
    else:
        held = int((cell & live_mask[y:y + 16, x:x + 16]).sum())
        status[slot] = 'held_ft' if held == int(cell.sum()) else 'recyclable'

# ── 交叉检查 ─────────────────────────────────────────────────────────
print('=' * 78)
print('FT 记录矩形 × 槽位: 哪些记录压到了"可用格"(free_blank)')
print('=' * 78)
hits = []
for c, (u0, v0, u1, v1) in sorted(rect_of.items()):
    ov = []
    for slot in range(1504):
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        if x < u1 and x + 16 > u0 and y < v1 and y + 16 > v0:
            # 重叠像素数
            X0, Y0 = max(x, u0), max(y, v0)
            X1, Y1 = min(x + 16, u1), min(y + 16, v1)
            ov.append((slot, status[slot], (X1 - X0) * (Y1 - Y0)))
    fb = [o for o in ov if o[1] == 'free_blank']
    if fb:
        hits.append((c, (u0, v0, u1, v1), ov, fb))
print('有 %d 条记录压到了可用格:' % len(hits))
for c, r, ov, fb in hits:
    nm = code2ch.get(c) or (chr(c) if 0x20 <= c < 0x7F else '')
    print('  0x%02X %-3s rec=(%4d,%3d,%4d,%4d):' % (c, nm, r[0], r[1], r[2], r[3]))
    for slot, st, n in ov:
        print('      slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d) 状态=%-10s 重叠 %3d px'
              % (slot, slot // 62, slot % 62, *tcslib.atlas_cell_xy_engine_view(slot), st, n))

# 被压住的可用格集合
blocked = {}
for c, r, ov, fb in hits:
    for slot, st, n in fb:
        blocked.setdefault(slot, []).append((c, n))
print()
print('★ 被 FT 记录压住的**可用格** %d 个:' % len(blocked))
for slot, who in sorted(blocked.items()):
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    print('    slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d)  被压 %d px  记录: %s'
          % (slot, slot // 62, slot % 62, x, y, sum(n for _c, n in who),
             ' '.join('0x%02X(%dpx)' % (c, n) for c, n in who)))

nb = sum(1 for s in status.values() if s == 'free_blank')
nh = sum(1 for s in status.values() if s == 'held_ft')
print()
print('统计: 在用 %d ; 可用(空白) %d ; 被活字形占着 %d ; 可回收 %d'
      % (sum(1 for s in status.values() if s == 'used'), nb, nh,
         sum(1 for s in status.values() if s == 'recyclable')))
print('⇒ **真正安全的可用格 = %d − %d = %d**' % (nb, len(blocked), nb - len(blocked)))

# 那些共用同一矩形的记录
print()
print('=' * 78)
print('共用同一矩形的记录组 (说明那个"蓝框"为什么会出现在四个格中间)')
print('=' * 78)
byrect = {}
for c, r in rect_of.items():
    byrect.setdefault(r, []).append(c)
for r, cs_ in sorted(byrect.items(), key=lambda kv: -len(kv[1])):
    if len(cs_) > 1:
        print('  rec=(%4d,%3d,%4d,%4d) 被 %d 条记录共用: %s  墨 %d px'
              % (r[0], r[1], r[2], r[3], len(cs_),
                 ' '.join('0x%02X' % c for c in sorted(cs_)),
                 int(ink[r[1]:r[3], r[0]:r[2]].sum())))
