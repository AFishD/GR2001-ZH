# -*- coding: utf-8 -*-
r"""lead_compare_sheet.py — 单格字库"逐字比对表": 每格上=盘上取到的字形, 下=字体模板

绿框 = 与模板逐像素完全一致; 黄框 = 差 1~3 px (渲染微差); 红框 = 差 >3 px (需要看)。
输出 lead_single_cell/compare_sheet.png + compare_report.json
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D            # noqa: E402
import glyph_geometry as G       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
OUT = os.path.join(HERE, 'lead_single_cell')
os.makedirs(OUT, exist_ok=True)

atlas = D.load_font(ISO)['atlas']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, view='engine'), dtype=np.uint8).reshape(H, W)
ink = gray < 128

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = cs['pair_of']
tpl = G.Templates()

items = []
for ch, (b1, b2) in pair_of.items():
    if not (0xA1 <= b1 < 0xB1):
        continue
    slot = (b1 - 0xA1) * 94 + (b2 - 0xA1)
    row, col = slot // 62, slot % 62
    x = 16 * col
    y = 2 + 16 * (row + (3 if row >= 12 else 0))
    items.append((slot, ch, b1, b2, x, y))
items.sort()

S = 2                       # 放大倍数
COLS = 32
tile_w, tile_h = 16 * S, (16 * 2 + 4) * S      # 上格 + 空隙 + 下格
ROWS = (len(items) + COLS - 1) // COLS
sheet = Image.new('RGB', (COLS * tile_w, ROWS * tile_h), (255, 255, 255))
px = sheet.load()

stats = {'exact': 0, 'near': 0, 'bad': 0, 'no_tpl': 0}
bad_list, near_list = [], []
for i, (slot, ch, b1, b2, x, y) in enumerate(items):
    cell = ink[y:y + 16, x:x + 16]
    t = tpl.get(ch)
    if t is None:
        stats['no_tpl'] += 1
        col_border = (150, 150, 150)
        diff = -1
    else:
        diff = int(np.logical_xor(cell, t).sum())
        if diff == 0:
            stats['exact'] += 1
            col_border = (0, 170, 0)
        elif diff <= 3:
            stats['near'] += 1
            near_list.append((ch, slot, diff))
            col_border = (230, 190, 0)
        else:
            stats['bad'] += 1
            bad_list.append((ch, slot, diff))
            col_border = (220, 0, 0)
    gx, gy = (i % COLS) * tile_w, (i // COLS) * tile_h
    # 上: 盘上格 (墨=黑)
    for yy in range(16):
        for xx in range(16):
            v = 0 if cell[yy, xx] else 255
            for dy in range(S):
                for dx in range(S):
                    px[gx + xx * S + dx, gy + yy * S + dy] = (v, v, v)
    # 下: 模板
    if t is not None:
        for yy in range(16):
            for xx in range(16):
                v = 0 if t[yy, xx] else 255
                for dy in range(S):
                    for dx in range(S):
                        px[gx + xx * S + dx, gy + (16 + 4) * S + yy * S + dy] = (v, v, v)
    # 边框 (用差异级别着色)
    for xx in range(tile_w):
        for dy in range(S):
            px[gx + xx, gy + dy] = col_border
            px[gx + xx, gy + tile_h - 1 - dy] = col_border

sheet.save(os.path.join(OUT, 'compare_sheet.png'))
doc = dict(total=len(items), grid='%dx%d' % (ROWS, COLS),
           exact=stats['exact'], near=stats['near'], bad=stats['bad'], no_template=stats['no_tpl'],
           near_list=near_list[:40], bad_list=bad_list[:80])
io.open(os.path.join(OUT, 'compare_report.json'), 'w', encoding='utf-8').write(
    json.dumps(doc, ensure_ascii=False, indent=1))
print('逐字比对表: %d 字 → %dx%d 格, 图 %dx%d' % (len(items), ROWS, COLS, sheet.width, sheet.height))
print('  **与字体模板逐像素完全一致 : %d**' % stats['exact'])
print('  差 1~3 px (渲染微差)       : %d  %s' % (stats['near'], near_list[:8]))
print('  差 >3 px (需要看)          : %d  %s' % (stats['bad'], bad_list[:12]))
print('  模板缺字 (字体里没有)       : %d' % stats['no_tpl'])
print('  PNG   → %s' % os.path.relpath(os.path.join(OUT, 'compare_sheet.png'), REPO))
print('  JSON  → %s' % os.path.relpath(os.path.join(OUT, 'compare_report.json'), REPO))
