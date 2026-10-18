# -*- coding: utf-8 -*-
r"""lead_single_cell_sheet.py — Lead 版"单格字库": 每个在用字取出自己的引擎格, 拼成一张总表

用途: 人眼核对"工具读到的格 = 该字自己的字形"。
坐标用**引擎口径**(x=16*col, y=2+16*(row+3*[row>=12])), 与 dump_font 的 CSV 口径无关(那列是 flat, 见待修项)。
输出:
  single_cell_sheet.png   总表 (一字一格, 按 slot 升序, 每格 16x16 原尺寸)
  single_cell_index.csv   总表位置 → 字符 / 码位 / slot / 引擎格坐标
"""
import csv
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
OUT = os.path.join(HERE, 'lead_single_cell')
os.makedirs(OUT, exist_ok=True)

atlas = D.load_font(ISO)['atlas']
W, H = atlas['w'], atlas['h']
gray = D.atlas_gray(atlas, view='engine')          # 引擎口径灰度 (0=墨)
img = Image.frombytes('L', (W, H), gray).convert('1', dither=Image.Dither.NONE)

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = cs['pair_of']
LEAD_LO, LEAD_HI = 0xA1, 0xB1

items = []
for ch, (b1, b2) in pair_of.items():
    if not (LEAD_LO <= b1 < LEAD_HI):
        continue
    slot = (b1 - 0xA1) * 94 + (b2 - 0xA1)
    row, col = slot // 62, slot % 62
    x = 16 * col
    y = 2 + 16 * (row + (3 if row >= 12 else 0))
    items.append((slot, ch, b1, b2, x, y))
items.sort()

COLS = 64
ROWS = (len(items) + COLS - 1) // COLS
sheet = Image.new('1', (COLS * 16, ROWS * 16), 1)   # 1 = 白
blank, idx = [], []
for i, (slot, ch, b1, b2, x, y) in enumerate(items):
    cell = img.crop((x, y, x + 16, y + 16))
    gx, gy = (i % COLS) * 16, (i // COLS) * 16
    sheet.paste(cell, (gx, gy))
    ink = sum(1 for yy in range(y, y + 16) for xx in range(x, x + 16) if gray[yy * W + xx] < 128)
    if ink == 0:
        blank.append((slot, ch))
    idx.append(dict(pos='r%d c%d' % (i // COLS + 1, i % COLS + 1), char=ch,
                    bytes='%02X%02X' % (b1, b2), slot=slot,
                    engine_x=x, engine_y=y, ink_px=ink))

sheet.save(os.path.join(OUT, 'single_cell_sheet.png'))
with io.open(os.path.join(OUT, 'single_cell_index.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(idx[0].keys()))
    w.writeheader()
    w.writerows(idx)

print('单格字库: %d 个字 → %d 行 x %d 列, 总表 %dx%d px' % (len(items), ROWS, COLS, sheet.width, sheet.height))
print('  PNG  → %s' % os.path.relpath(os.path.join(OUT, 'single_cell_sheet.png'), REPO))
print('  索引 → %s' % os.path.relpath(os.path.join(OUT, 'single_cell_index.csv'), REPO))
print('  空白格(应为 0): %d %s' % (len(blank), blank[:6] if blank else '✓'))
ink_total = sum(1 for v in gray if v < 128)
print('  图集墨点: %d' % ink_total)
# 交叉: 与 dump_font 的 charset CSV 比对 (它的 cell_x 是 flat, 这里算引擎, 差应当恒定)
csvp = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'font', 'GR_ZH98_font_charset.csv')
if os.path.isfile(csvp):
    rows = list(csv.DictReader(io.open(csvp, encoding='utf-8-sig')))
    cm = {r['char']: (int(r['cell_x']), int(r['cell_y'])) for r in rows if r.get('kind') == 'pair' and r.get('cell_x')}
    deltas = set()
    for slot, ch, b1, b2, x, y in items:
        if ch in cm:
            cx, cy = cm[ch]
            deltas.add((cx - x, cy - y))
    print('  与 dump_font CSV 的坐标差集合 (应只含 flat 偏移): %s' % sorted(deltas)[:6])
