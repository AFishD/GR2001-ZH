# -*- coding: utf-8 -*-
r"""space_bands.py -- 现役图集逐行墨迹占位（只读）：把"非网格内容"的 y 带找出来。

用途: 验证 h=592 新增的网格 row 28..32（y=498/514/530/546/562）**不会撞上**
      EN 带 / large 键盘带 / 其他 record 面的带。
"""
import argparse
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import dump_font as D          # noqa: E402
import tcslib                  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113B.iso'))
    ap.add_argument('--iso2', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                   'GR_ZH113b.iso'))
    a = ap.parse_args()
    p = a.iso if os.path.isfile(a.iso) else a.iso2
    g = D.load_font(p)
    at = g['atlas']
    w, h = at['w'], at['h']
    gray = np.frombuffer(D.atlas_gray(at, view='engine'), dtype=np.uint8).reshape(h, w)
    ink = (gray == 0)
    per_row = ink.sum(axis=1)
    print('== %s  图集 %dx%d ==' % (os.path.basename(p), w, h))
    # 逐行
    print('\n-- 有墨的 y 行连续段 --')
    runs, cur = [], None
    for y in range(h):
        if per_row[y] > 0 and cur is None:
            cur = y
        elif per_row[y] == 0 and cur is not None:
            runs.append((cur, y))
            cur = None
    if cur is not None:
        runs.append((cur, h))
    for y0, y1 in runs:
        seg = ink[y0:y1]
        xs = np.flatnonzero(seg.any(axis=0))
        print('   y[%3d,%3d) 共 %2d 行  墨=%7d  x 范围 [%d, %d]  行墨量 min/max = %d/%d'
              % (y0, y1, y1 - y0, int(seg.sum()), int(xs.min()), int(xs.max()),
                 int(seg.sum(axis=1).min()), int(seg.sum(axis=1).max())))
    # 关键区间
    print('\n-- 新网格行会落在哪里 --')
    for r in range(26, 34):
        y = tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))
        seg = ink[y:y + 16]
        xs = np.flatnonzero(seg.any(axis=0)) if seg.size else []
        # 网格列之外的墨（x>=992 或落在 62 列之间的缝）
        n = int(seg.sum())
        print('   row %-2d y=[%3d,%3d)  墨=%-7d  %s' %
              (r, y, y + 16, n,
               ('x 范围 [%d,%d]' % (xs.min(), xs.max())) if len(xs) else '全空'))
    # EN 带 / 键盘带 附近
    print('\n-- 450~512 逐行墨量 --')
    for y in range(448, h):
        if per_row[y]:
            xs = np.flatnonzero(ink[y])
            print('   y=%3d 墨=%-6d x[%d,%d]' % (y, int(per_row[y]), int(xs.min()), int(xs.max())))
    # face 记录带的 v0/v1
    print('\n-- FONT.RES 各 face 的 fld / 记录 v 带（前 6 条非空） --')
    for nm, fld, recs in g['faces']:
        vs = sorted({(r[3], r[5]) for r in recs if r[2] or r[3] or r[4] or r[5]})
        print('   face %-10s fld[1]=%-3d nrec=%-4d v 带种类=%d 前 8 = %s'
              % (nm, fld[1], len(recs), len(vs), vs[:8]))


main()
