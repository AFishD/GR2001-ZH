# -*- coding: utf-8 -*-
r"""p2_survey.py — 现役盘 GR_ZH109 的图集"空白可用格"普查 (为高 lead 探针选落点)。

只读。报告:
  · 每个候选 slot 的引擎格 (row, col) → (x, y): 墨量、是否被 FT 记录矩形压着、是否在被跳过的带里;
  · 行 19..27 的可用列清单;
  · FT 记录矩形 (3 个 face) 的实际覆盖范围 —— 用来判断"哪些行其实是 ASCII 带"。
"""
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

ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
ink = gray == 0
print('atlas %dx%d psm=0x%02X px_off=0x%X; 全图墨像素 %d' % (W, H, atlas['psm'], atlas['px_off'], int(ink.sum())))

# ---- FT 记录矩形 (3 个 face 全部) ----
rect = np.zeros((H, W), dtype=bool)
nrec = 0
for (nm, _junk, recs) in faces:
    for i, r in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 <= u0 or v1 <= v0:
            continue
        nrec += 1
        rect[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True
print('faces=%s; 非空 FT 记录矩形 %d 条; 覆盖 %d px'
      % ([(x[0], len(x[2])) for x in faces], nrec, int(rect.sum())))

fdef = [x for x in faces if x[0] == 'default'][0][2]
print('\n== default face 的记录矩形按 y 分桶 ==')
from collections import defaultdict                                             # noqa: E402
band = defaultdict(list)
for i, r in enumerate(fdef):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 <= u0 or v1 <= v0:
        continue
    band[(v0 // 16) * 16].append((i + 0x20, u0, v0, u1, v1))
for k in sorted(band):
    lst = band[k]
    print('  y~%3d : %2d 条  码 %s' % (k, len(lst), ' '.join('%02X' % c for c, *_ in lst[:26])))


def cell_report(slot):
    row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if y + tcslib.CH > H:
        return dict(slot=slot, row=row, col=col, x=x, y=y, ink=-1, rec=-1, note='越出图集下沿')
    c = ink[y:y + tcslib.CH, x:x + tcslib.CW]
    r = rect[y:y + tcslib.CH, x:x + tcslib.CW]
    return dict(slot=slot, row=row, col=col, x=x, y=y, ink=int(c.sum()), rec=int(r.sum()),
                conflict=tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((row, col)),
                skip_band=(194 <= y <= 241))


print('\n== 候选 slot (高 lead 用) ==')
for lead in (0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4):
    for trail in (0xA1, 0xA2, 0xA3, 0xB2, 0xB3, 0xB4):
        slot = (lead - 0xA1) * 94 + (trail - 0xA1)
        d = cell_report(slot)
        print('  lead=%02X trail=%02X slot=%4d row=%2d col=%2d (%4d,%3d) 墨=%4d 记录压=%4d %s%s'
              % (lead, trail, slot, d['row'], d['col'], d['x'], d['y'], d['ink'], d['rec'],
                 '★冲突:%s ' % d['conflict'] if d.get('conflict') else '',
                 '(跳过带)' if d.get('skip_band') else ''))

print('\n== 每个网格行的空列数 (行 0..27; 空 = 墨=0 且 记录压=0) ==')
for row in range(0, 28):
    y = tcslib.GRID_Y0 + tcslib.CH * (row + (tcslib.GRID_SKIP_ROWS if row >= tcslib.GRID_SKIP_ROW else 0))
    if y + tcslib.CH > H:
        print('  row %2d y=%3d  越界' % (row, y))
        continue
    free = []
    for col in range(tcslib.NCOL):
        slot = row * tcslib.NCOL + col
        d = cell_report(slot)
        if d['ink'] == 0 and d['rec'] == 0 and not d.get('conflict'):
            free.append(col)
    print('  row %2d y=%3d  空列 %3d/%d  %s' % (row, y, len(free), tcslib.NCOL,
                                                ('' if len(free) > 40 else str(free))))

print('\n== ASCII 带的真实高度 (哪些 y 有 FT 记录矩形) ==')
ys = np.where(rect[:, 0:W].sum(axis=1) > 0)[0]
print('  有记录矩形的 y: %s ... %s' % (list(ys[:12]), list(ys[-12:])))
print('  y=434..449 记录压 px = %d' % int(rect[434:450, :].sum()))
print('  y=450..465 记录压 px = %d' % int(rect[450:466, :].sum()))
print('  y=466..481 记录压 px = %d' % int(rect[466:482, :].sum()))
print('  y=482..497 记录压 px = %d' % int(rect[482:498, :].sum()))
