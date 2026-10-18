# -*- coding: utf-8 -*-
r"""lead_zoom28.py — 把 y=482 那 28 格高倍放大, 直接看是什么字 (含期望模板对照)"""
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D            # noqa: E402
import glyph_geometry as G       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
OUT = os.path.join(HERE, 'lead_single_cell')
atlas = D.load_font(ISO)['atlas']
img = Image.frombytes('L', (atlas['w'], atlas['h']),
                      D.atlas_gray(atlas, view='engine')).convert('1', dither=Image.Dither.NONE)
tpl = G.Templates()
cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))

# code -> char (单字节)
code2ch = {v: k for k, v in cs['codes'].items()}
S = 10
Z = 16 * S
rows = []
for i in range(28):
    x = i * 16
    code = 0x80 + i
    ch = code2ch.get(code, '?')
    rows.append((ch, code, x))

# 每行 7 组: [盘上格][模板] 交替, 组内上方留 2px 分隔
cols = 7
tile_w = Z + 8
tile_h = Z + 8
sheet = Image.new('1', (cols * tile_w * 2, ((len(rows) + cols - 1) // cols) * tile_h), 1)
for i, (ch, code, x) in enumerate(rows):
    cell = img.crop((x, 482, x + 16, 498)).resize((Z, Z), Image.NEAREST)
    t = tpl.get(ch)
    ti = Image.new('1', (16, 16), 1)
    if t is not None:
        for yy in range(16):
            for xx in range(16):
                if t[yy, xx]:
                    ti.putpixel((xx, yy), 0)
    ti = ti.resize((Z, Z), Image.NEAREST)
    gx = (i % cols) * tile_w * 2
    gy = (i // cols) * tile_h
    sheet.paste(cell, (gx, gy))
    sheet.paste(ti, (gx + tile_w, gy))
sheet.save(os.path.join(OUT, 'zoom28_pairs.png'))
print('高倍对照 (左=盘上格, 右=模板): %s  %dx%d'
      % (os.path.relpath(os.path.join(OUT, 'zoom28_pairs.png'), REPO), sheet.width, sheet.height))
print('顺序 (左→右, 上→下):', ' '.join('%s(%02X)' % (c, b) for c, b, _ in rows))
