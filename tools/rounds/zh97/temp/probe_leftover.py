# -*- coding: utf-8 -*-
r"""probe_leftover.py — 侦察: ① 20 个"人名"字是否还在用 ② 未使用区域的残墨在哪 ③ "92" 出处"""
import csv
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

CH20 = '珍琳费贾赖辉辛迈郑闫阮阳陈隆雅韦魏鲍鹏麦'
TDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'text')

print('=' * 70)
print('① 20 个"人名"字在当前文本表里的使用情况 (GR_ZH97/text)')
print('=' * 70)
hits = {c: [] for c in CH20}
for n in sorted(os.listdir(TDIR)):
    if not n.endswith('.csv'):
        continue
    for r in csv.DictReader(io.open(os.path.join(TDIR, n), encoding='utf-8-sig')):
        t = r.get('text_edited') or ''
        for c in CH20:
            if c in t:
                hits[c].append('%s/%s' % (n.replace('GR_ZH97_text_', '').replace('.csv', ''), r.get('id')))
for c in CH20:
    n = len(hits[c])
    print('  %s : %s%s' % (c, n, ('  ← ' + ', '.join(hits[c][:3])) if n else ''))

print()
print('=' * 70)
print('② 未使用区域的残墨 (引擎口径图集 1024x512)')
print('=' * 70)
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'release', 'font', 'GR_ZH97_font_atlas_1x.png')
im = Image.open(P).convert('L')
px = im.load()
W, H = im.size
print('图集 %dx%d' % (W, H))

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
# 已用对偶格
used = set()
for ch, (b1, b2) in cs['pair_of'].items():
    if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
    used.add((x // 16, y // 16))
print('已用对偶格: %d 个 (按 16x16 网格计)' % len(used))

# 逐格统计: 不在已用格里的墨
grid_ink = {}
for gy in range(H // 16):
    for gx in range(W // 16):
        if (gx, gy) in used:
            continue
        n = 0
        for y in range(gy * 16, gy * 16 + 16):
            for x in range(gx * 16, gx * 16 + 16):
                if px[x, y] < 128:
                    n += 1
        if n:
            grid_ink[(gx, gy)] = n
tot = sum(grid_ink.values())
print('**未使用格里有墨的: %d 格 / 共 %d 像素**' % (len(grid_ink), tot))
by_row = {}
for (gx, gy), n in grid_ink.items():
    by_row.setdefault(gy, []).append((gx, n))
print('按网格行分布 (行: 格数/像素):')
for gy in sorted(by_row):
    tot_r = sum(n for _, n in by_row[gy])
    print('   row %2d : %2d 格 / %5d px   cols=%s' % (gy, len(by_row[gy]), tot_r,
          ','.join(str(gx) for gx, _ in sorted(by_row[gy])[:14])))
print()
print('最大 15 个残墨格:')
for (gx, gy), n in sorted(grid_ink.items(), key=lambda kv: -kv[1])[:15]:
    print('   (col %2d, row %2d) = 像素 x=%4d..%4d y=%4d..%4d : %3d px'
          % (gx, gy, gx * 16, gx * 16 + 15, gy * 16, gy * 16 + 15, n))

print()
print('=' * 70)
print('③ 报告里 "92" 的出处')
print('=' * 70)
import subprocess
for pat in ('92', '回收'):
    pass
rp = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'release', '字库报告.md')
if os.path.isfile(rp):
    for i, line in enumerate(io.open(rp, encoding='utf-8'), 1):
        if '回收' in line or '92' in line:
            print('  字库报告.md L%d: %s' % (i, line.strip()[:130]))
