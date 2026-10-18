# -*- coding: utf-8 -*-
r"""lead_unused_slots.py — 关键测量: **没被 charset 占用的对偶格**里还有没有墨

round49 判据 = 墨 ∧ ¬(已用对偶格) ∧ ¬(FT 窗) ⇒ 已用格被整体保护, 但**空格从未被检查**。
本脚本逐格列出 1504 个槽位的状态, 找出"空格有墨"的格子并输出标注图。
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'GR_ZH101.iso')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'temp', 'r52')
os.makedirs(OUT, exist_ok=True)
w = D.load_font(ISO)
ad = w['atlas']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = cs['pair_of']
slot_of = {}
for ch, (b1, b2) in pair_of.items():
    if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
        continue
    slot_of[tcslib.pair_slot(b1, b2)] = ch
print('charset 占用槽位 %d 个' % len(slot_of))

cap = 1504
unused_ink, unused_blank = [], []
for slot in range(cap):
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if not (0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H):
        continue
    n = int(ink[y:y + 16, x:x + 16].sum())
    if slot in slot_of:
        continue
    (unused_ink if n else unused_blank).append((slot, x, y, n))

print()
print('=' * 78)
print('★ 空格 (未被 charset 占用的槽位) 的墨量统计')
print('=' * 78)
print('  空格总数 %d ; **有墨的空格 %d 个 (合计 %d px)** ; 干净空格 %d 个'
      % (len(unused_ink) + len(unused_blank), len(unused_ink),
         sum(t[3] for t in unused_ink), len(unused_blank)))
print()
print('  有墨的空格 (按墨量, 全部):')
for slot, x, y, n in sorted(unused_ink, key=lambda t: -t[3]):
    print('     slot=%-4d row=%-2d col=%-2d cell=(%4d,%3d) 墨 %3d px' % (slot, slot // 62, slot % 62, x, y, n))

# 也检查: 已用格里有没有"墨量与模板不符"(说明格里是别人的字)
try:
    sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
    import glyph_geometry as G
    T = G.Templates()
    bad = []
    for slot, ch in slot_of.items():
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        t = T.get(ch)
        if t is None:
            continue
        cell = ink[y:y + 16, x:x + 16]
        inter = int(np.logical_and(cell, t).sum()); uni = int(np.logical_or(cell, t).sum())
        iou = inter / max(1, uni)
        if iou < 0.99:
            bad.append((ch, slot, x, y, int(cell.sum()), round(iou, 4)))
    print()
    print('  已用格里 IoU<0.99 的 (说明格里不是这个字): %d 个' % len(bad))
    for ch, slot, x, y, n, iou in sorted(bad, key=lambda t: t[5])[:20]:
        print('     %s slot=%-4d cell=(%4d,%3d) 墨 %3d IoU %.4f' % (ch, slot, x, y, n, iou))
except Exception as e:
    print('  (模板比对跳过: %s)' % e)

# 标注图: 空格有墨 = 橙色
rgb = np.full((H, W, 3), 255, dtype=np.uint8)
for slot in slot_of:
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    rgb[y:y + 16, x:x + 16] = (210, 232, 255)
for slot, x, y, n in unused_ink:
    rgb[y:y + 16, x:x + 16] = (255, 120, 0)
rgb[ink & (rgb == 255).all(axis=2)] = (255, 0, 0)
im = Image.fromarray(rgb)
im.resize((W * 2, H * 2), Image.NEAREST).save(os.path.join(OUT, 'unused_slot_map.png'))
print()
print('→ %s  (淡蓝=已用格 / 橙=空格但有墨 / 红=两者之外的墨)'
      % os.path.relpath(os.path.join(OUT, 'unused_slot_map.png'), REPO))
