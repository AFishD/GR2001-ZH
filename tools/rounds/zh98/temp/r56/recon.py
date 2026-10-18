# -*- coding: utf-8 -*-
"""round56 侦察: GR_ZH105 的字库格位/可用格分布/SFXML 属性/全盘扫描基线 (只读)。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import repack_font as RF                                             # noqa: E402
import dump_font                                                     # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'GR_ZH105.iso')
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH

print('=' * 78)
print('ISO', ISO)
print('sha256', tcslib.sha256_file(ISO))
res = RF.plan(ISO, verbose=True)
s = res['summary']
print(json.dumps({k: s[k] for k in ('changed', 'pixels_changed', 'code_changes',
                                    'cells', 'glyphs', 'capacity')},
                 ensure_ascii=False, indent=1))

cells, cls, usable = res['cells'], res['cls'], res['usable']
used_slots = sorted(s0 for s0, _ in res['items'])
print('usable %d  used %d' % (len(usable), len(used_slots)))
print('used slot min/max %d/%d' % (used_slots[0], used_slots[-1]))
print('used >= 1175: %d' % len([x for x in used_slots if x >= 1175]))
print('usable < 1175: %d' % len([x for x in usable if x < 1175]))
print('usable >= 1175: %d' % len([x for x in usable if x >= 1175]))
print('slots 0..1174 that are NOT usable: %d'
      % sum(1 for x in range(1175) if cls[x][0] != 'usable'))
bad = [(x, x // NCOL, x % NCOL, cls[x][0], cls[x][1]) for x in range(1175)
       if cls[x][0] != 'usable']
for b in bad[:60]:
    print('   nonusable %s' % (b,))
print('slots 1175..1503 that ARE usable: %d'
      % sum(1 for x in range(1175, 1504) if cls[x][0] == 'usable'))

# 逐个可用格的分布 (按行统计)
rowstat = {}
for x in usable:
    rowstat.setdefault(x // NCOL, []).append(x % NCOL)
print('usable by row:', {r: len(c) for r, c in sorted(rowstat.items())})
free_slots = [x for x in range(1504) if x not in set(used_slots)]
print('free slots total %d' % len(free_slots))
frow = {}
for x in free_slots:
    frow.setdefault(x // NCOL, []).append(x % NCOL)
print('free slots by row:', {r: len(c) for r, c in sorted(frow.items())})
# 非 "used" 的格按状态分类 (font_cell_map 口径的雏形)
cnt = {}
for x in range(1504):
    k = cls[x][0]
    cnt[k] = cnt.get(k, 0) + 1
print('classify counts:', cnt)

# FT 记录矩形分布: 哪些 y 带
protect, rects = RF.protect_mask(res['faces'], 1024, 512)
ys = np.where(protect.any(axis=1))[0]
print('protect rows y=%d..%d, px=%d' % (ys.min(), ys.max(), int(protect.sum())))
bands = []
prev = None
for y in ys:
    if prev is None or y != prev + 1:
        bands.append([int(y), int(y)])
    else:
        bands[-1][1] = int(y)
    prev = y
print('protect y bands:', bands)
print('faces:', [f[0] for f in res['faces']], 'nrects', [len(f[2]) for f in res['faces']])
# 每个 face 的非空矩形范围
for (nm, _fld, rs) in res['faces']:
    live = [r for r in rs if r[4] > r[2] and r[5] > r[3]]
    if live:
        print('  face %-8s live %3d  v0 %d..%d  u1max %d'
              % (nm, len(live), min(r[3] for r in live), max(r[5] for r in live),
                 max(r[4] for r in live)))
