# -*- coding: utf-8 -*-
r"""lead_ident_single.py — 28 个单字节格到底装的是哪个字: 与全部模板比对取最佳匹配"""
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
atlas = D.load_font(ISO)['atlas']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, view='engine'), dtype=np.uint8).reshape(H, W)
ink = gray < 128
tpl = G.Templates()

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
rep = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'lead_run51',
                                     'single_cell_report.json'), encoding='utf-8'))
bad = [r for r in rep['findings'] if r['kind'] == 'single']

# 全部候选模板 (对偶 + 单字节 + ASCII 可见字符)
cands = list(cs['pair_of'].keys()) + [ch for ch in cs['codes'] if not ch.isspace()]
print('候选模板 %d 个' % len(cands))

print()
print('%-4s %-5s %-22s %-10s %-8s %s' % ('字', '码', '记录矩形', '盘上格→最像', 'IoU', '次佳'))
rows = []
for r in bad:
    x, y = r['cell_x'], r['cell_y']
    cell = ink[y:y + 16, x:x + 16]
    best = []
    for ch in cands:
        t = tpl.get(ch)
        if t is None:
            continue
        inter = int(np.logical_and(cell, t).sum())
        union = int(np.logical_or(cell, t).sum())
        if union == 0:
            continue
        iou = inter / union
        best.append((iou, ch))
    best.sort(reverse=True)
    top = best[:3]
    rows.append(dict(char=r['char'], code=r['code'], rect=r['note'],
                     top=[(round(i, 3), c) for i, c in top]))
    print('%-4s %-5s %-22s %-10s %-8s %s'
          % (r['char'], r['code'], r['note'], top[0][1], round(top[0][0], 3),
             ', '.join('%s %.2f' % (c, i) for i, c in top[1:3])))

print()
hit = sum(1 for r in rows if r['top'] and r['top'][0][0] > 0.8)
print('最佳匹配 IoU > 0.8 的: %d / %d' % (hit, len(rows)))
print('最佳匹配 == 本字 的: %d / %d' % (sum(1 for r in rows if r['top'] and r['top'][0][1] == r['char']), len(rows)))
io.open(os.path.join(HERE, 'lead_single_cell', 'ident_single.json'), 'w', encoding='utf-8').write(
    json.dumps(rows, ensure_ascii=False, indent=1))
print('→ work/builds/GR_ZH98/temp/lead_single_cell/ident_single.json')
