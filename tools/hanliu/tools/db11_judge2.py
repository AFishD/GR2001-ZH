# [hanliu 收编] 原件: C:/gr_build/tmp/zh8b/db11_judge2.py (逐字复制)。原件保留于原处未动。
# -*- coding: utf-8 -*-
"""db11_judge2.py — 扫描盘逐字单调匹配判定 (v7)
对每行 8 项: 从行首起按项序单调滑窗搜索 (窗宽 ±20 snap), 每项取局部最优 NCC;
阈值 ≥0.5 = 正确字形。同时输出每项匹配 x 与墨簇宽 (blank/dash 体检)。
用法: python db11_judge2.py <snap> <tag> [json_out]
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import os, sys, json
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
OUT = os.path.join(REPO_ROOT, 'work', 'tmp', 'zh8')
SNAP = sys.argv[1]
TAG = sys.argv[2]
JOUT = sys.argv[3] if len(sys.argv) > 3 else None
SX = 583.0 / 640.0
KERN = 1.0
CELL_W, CELL_H, GRIDY, NCOL = 12, 15, 128, 41

man = json.load(open(OUT + r'\db9_scan_manifest.json'))
rows = man['rows']
n_pair = man['n_pair']
pak = open(OUT + r'\COMMON_PAK_ZH8.bin', 'rb').read()
ATLAS = np.frombuffer(bytes(pak[0x1069:0x1069 + 512 * 512]), dtype=np.uint8).reshape(512, 512).astype(float)
INK = (31.0 - ATLAS) / 31.0

def cell_of(item):
    if len(item) == 2:
        slot = (item[0] - 0xA1) * 94 + (item[1] - 0xA1)
    else:
        c = item[0]
        slot = n_pair + c - 0xAF - (c > 0xB1) - (c > 0xB5) - (c > 0xE7) - (c > 0xF1)
    col, row = slot % NCOL, slot // NCOL
    x = 20 + CELL_W * col
    y = GRIDY + CELL_H * row
    return INK[y:y + CELL_H, x:x + CELL_W]

scr = np.asarray(Image.open(SNAP).convert('L'), dtype=float) / 255.0

def ncc(a, b):
    a = a - a.mean(); b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 1e-6 else 0.0

GW = int(round(12 * SX))   # 11
# 行布局: rows0-9 = 左列 (y=110..335, x 40..230); rows10-17 = 右列 (y=110..285, x 360..570)
# rows18-19 = 本帧不可见 (尾对在第 10 行右列后 2 行空) → 跳过并标注
def row_geom(ri):
    if ri < 10:
        return 110 + 25 * ri, 40, 232
    if ri < 18:
        return 110 + 25 * (ri - 10), 358, 575
    return None

results = []
for ri, items in enumerate(rows):
    g = row_geom(ri)
    if g is None:
        results.append({'row': ri, 'skip': 'not-on-page'})
        continue
    y0, x_lo, x_hi = g
    band = scr[y0 - 3:y0 + 13, :]          # 16 行
    x = float(x_lo)
    per = []
    for it in items:
        tpl = cell_of(it)
        t = np.asarray(Image.fromarray((tpl * 255).astype(np.uint8)).resize(
            (GW, band.shape[0]), Image.BILINEAR), dtype=float) / 255.0
        best = (-2.0, 0)
        xa = int(x) - 4
        xb = int(x + 38 * SX) + 6
        for xi in range(max(x_lo, xa), min(x_hi - GW, xb)):
            s = ncc(t, band[:, xi:xi + GW])
            if s > best[0]:
                best = (s, xi)
        per.append({'ncc': round(best[0], 3), 'x': best[1]})
        x = best[1] + GW + 1.0            # 单调推进
    ok = sum(1 for p in per if p['ncc'] >= 0.5)
    results.append({'row': ri, 'per': per, 'ok': ok, 'n': len(items)})
    print('row%02d %2d/%d  %s' % (ri, ok, len(items),
          ' '.join('%.2f' % p['ncc'] for p in per)))
tot = [p for r in results if 'per' in r for p in r['per']]
ok = sum(1 for p in tot if p['ncc'] >= 0.5)
print('[%s] 总格 %d, NCC≥0.5: %d (%.1f%%)' % (TAG, len(tot), ok, 100.0 * ok / len(tot)))
if JOUT:
    json.dump(results, open(JOUT, 'w'), indent=1)
