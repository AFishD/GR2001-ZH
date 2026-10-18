# -*- coding: utf-8 -*-
r"""lead_crop_single.py — 把 28 个"不同字形"的单字节格裁出来看看 (盘上到底是什么)"""
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
import dump_font as D            # noqa: E402
import glyph_geometry as G       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
OUT = os.path.join(HERE, 'lead_single_cell')
atlas = D.load_font(ISO)['atlas']
W, H = atlas['w'], atlas['h']
img = Image.frombytes('L', (W, H), D.atlas_gray(atlas, view='engine')).convert('1', dither=Image.Dither.NONE)
tpl = G.Templates()

rep = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'lead_run51',
                                     'single_cell_report.json'), encoding='utf-8'))
bad = [r for r in rep['findings'] if r['kind'] == 'single']
print('单字节不匹配 %d 个' % len(bad))

S = 4
tile = 16 * S
cols = 10
rows = (len(bad) * 2 + cols - 1) // cols
sheet = Image.new('1', (cols * tile, rows * tile), 1)
for i, r in enumerate(bad):
    x, y = r['cell_x'], r['cell_y']
    cell = img.crop((x, y, x + 16, y + 16))
    t = tpl.get(r['char'])
    ti = Image.new('1', (16, 16), 1)
    if t is not None:
        for yy in range(16):
            for xx in range(16):
                if t[yy, xx]:
                    ti.putpixel((xx, yy), 0)
    for k, im2 in enumerate((cell, ti)):
        idx = i * 2 + k
        gx, gy = (idx % cols) * tile, (idx // cols) * tile
        sheet.paste(im2.resize((tile, tile), Image.NEAREST), (gx, gy))
sheet.save(os.path.join(OUT, 'single_mismatch_pairs.png'))
print('裁图 → %s (%dx%d) 每两格一组: 左=盘上, 右=模板' %
      (os.path.relpath(os.path.join(OUT, 'single_mismatch_pairs.png'), REPO), sheet.width, sheet.height))
print()
print('前 8 个的码位 / 记录 / 墨点:')
for r in bad[:8]:
    print('  %s 码 %s  %s  disk_ink=%s tpl_ink=%s diff=%s iou=%s'
          % (r['char'], r['code'], r['note'], r['disk_ink'], r['tpl_ink'], r['diff_px'], r['iou']))
# 这些字在文本里用不用?
TDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text')
use = {}
for n in sorted(os.listdir(TDIR)):
    if not n.endswith('.csv'):
        continue
    for row in csv.DictReader(io.open(os.path.join(TDIR, n), encoding='utf-8-sig')):
        t = row.get('text_edited') or ''
        for r in bad:
            if r['char'] in t:
                use[r['char']] = use.get(r['char'], 0) + 1
print()
print('这 28 个字在译文里的使用次数:')
print('  ' + ', '.join('%s×%d' % (k, v) for k, v in sorted(use.items(), key=lambda kv: -kv[1])) or '  (都没用到)')
print('  合计出现: %d 次' % sum(use.values()))
