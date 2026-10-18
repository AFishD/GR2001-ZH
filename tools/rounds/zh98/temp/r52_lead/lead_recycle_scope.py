# -*- coding: utf-8 -*-
r"""lead_recycle_scope.py — 到底哪些格子**真能回收**?

回收一个格子 = 把它的墨清掉, 且**没有任何活字体会因此受损**。判据:

  可清 = 墨 ∧ ¬(在用对偶格) ∧ ¬(**活** FT 记录矩形)

  活 FT 记录 = 该 code 是"引擎真会画的":
      · 我们的单字节码 (charset.codes) —— 但若该字在正文里 0 次出现, 它也是"没使用的字" ⇒ 可回收
      · 可打印 ASCII 0x20..0x7E (正文用到 84 个)
      · 引擎硬编码: 0x7B/0x7D 滚动箭头; 0xB1/0xB5 图标码 (记录槽位必须留)
  非活 FT 记录 = 剩下的 (0xA1..0xAF, 0xB0 等) ⇒ 它们的墨是"没人要的旧字" ⇒ **可回收**

再回答: 回收后能**多出几个可用对偶格**。
"""
import csv
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

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH102', 'GR_ZH102.iso')
TEXTDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH102', 'text')
w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128
cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
code2ch = {int(v): k for k, v in cs['codes'].items()}

# ── 正文里各字符出现次数 (3 张可注入表) ──────────────────────────────
occ = {}
for fn in os.listdir(TEXTDIR):
    if not (fn.endswith('_text_long.csv') or fn.endswith('_text_long_nowrap.csv')
            or fn.endswith('_text_short.csv')):
        continue
    with io.open(os.path.join(TEXTDIR, fn), encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            for ch in (row.get('text_edited') or ''):
                occ[ch] = occ.get(ch, 0) + 1

unused_single = sorted(c for c in code2ch if occ.get(code2ch[c], 0) == 0)
print('单字节码 %d 个; 其中**正文 0 次出现**的 %d 个: %s'
      % (len(code2ch), len(unused_single),
         ' '.join('%02X=%s' % (c, code2ch[c]) for c in unused_single)))
print()

# ── FT 记录 ──────────────────────────────────────────────────────────
rec = [r for f, _x, rs in faces if f == 'large' for r in rs]
rect_of = {}
for idx, r in enumerate(rec):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 > u0 and v1 > v0:
        rect_of[idx + 0x20] = (u0, v0, u1, v1)

KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}                    # 引擎硬编码 / 图标记录槽


def is_live(code):
    if code in KEEP_HARD:
        return True
    if 0x20 <= code <= 0x7E:
        return True                                      # 可打印 ASCII: 正文用到
    if code in code2ch:
        return occ.get(code2ch[code], 0) > 0             # 我们的单字节字: 正文真用到才算活
    return False


dead_recs = sorted(c for c in rect_of if not is_live(c))
live_recs = sorted(c for c in rect_of if is_live(c))
print('FT 记录 %d 条: 活 %d 条, **非活(其墨没人要)** %d 条' % (len(rect_of), len(live_recs), len(dead_recs)))
print('  非活记录: %s' % ' '.join('0x%02X' % c for c in dead_recs))
for c in dead_recs:
    u0, v0, u1, v1 = rect_of[c]
    print('    0x%02X rec=(%4d,%3d,%4d,%4d) 墨 %3d px' % (c, u0, v0, u1, v1, int(ink[v0:v1, u0:u1].sum())))

# ── 可回收的墨 ───────────────────────────────────────────────────────
live_mask = np.zeros((H, W), dtype=bool)
for c in live_recs:
    u0, v0, u1, v1 = rect_of[c]
    live_mask[v0:v1, u0:u1] = True
used_mask = np.zeros((H, W), dtype=bool)
slot_of = {}
for ch, (b1, b2) in cs['pair_of'].items():
    if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
        s = tcslib.pair_slot(b1, b2)
        slot_of[s] = ch
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        used_mask[y:y + 16, x:x + 16] = True

recyclable = ink & ~used_mask & ~live_mask
print()
print('可回收墨 = 墨 ∧ ¬在用格 ∧ ¬活记录 = **%d px**' % int(recyclable.sum()))

# 回收后能多出几个可用对偶格
gain = []
for slot in range(1504):
    if slot in slot_of:
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        continue
    cell = ink[y:y + 16, x:x + 16]
    if not cell.any():
        continue                                     # 本来就空白 (已算可用格)
    rec_part = int((cell & live_mask[y:y + 16, x:x + 16]).sum())
    recov = int((cell & recyclable[y:y + 16, x:x + 16]).sum())
    if rec_part == 0 and recov:
        gain.append((slot, slot // 62, slot % 62, x, y, int(cell.sum()), recov))
print()
print('★ 回收后**新变成可用格**的槽位 %d 个:' % len(gain))
for slot, row, col, x, y, n, r in gain:
    print('    slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d) 现有墨%3d, 其中可回收 %3d' % (slot, row, col, x, y, n, r))
print()
print('⇒ 可用格: 239 + %d = **%d**' % (len(gain), 239 + len(gain)))
