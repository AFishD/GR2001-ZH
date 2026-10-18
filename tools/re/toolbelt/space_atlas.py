# -*- coding: utf-8 -*-
r"""space_atlas.py -- 现役字库图集的**墨迹几何实测**（只读）。

决定性的一个数: 现役 1504 个字形，墨迹在**它自己的 16x16 格内**的最大 bbox 是多少?
若最大墨迹 ≤ 15 宽 x 15 高，则 "格距 16->15（双轴）" 是**像素级无损重排**（不需要重渲字形）,
这是"零额外字节"路线唯一的立足点。

另测:
  * 每行墨迹 bbox 直方图（找有没有墨落在格内第 15 列/行）
  * 图集总墨迹 texel 数 与 采样窗冲突
  * EN 带 [452,468) / 键盘带 / 图标窗 的墨迹占用

用法: python tools/re/toolbelt/space_atlas.py [--iso PATH] [--json OUT]
"""
import argparse
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import dump_font as D          # noqa: E402
import tcslib                  # noqa: E402

DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
EN_BAND = (452, 468)
ICON_WIN = (198, 222)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=DEFAULT_ISO)
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r78', 'atlas_ink.json'))
    a = ap.parse_args()
    g = D.load_font(a.iso)
    at = g['atlas']
    w, h = at['w'], at['h']
    gray = D.atlas_gray(at, view='engine')
    print('atlas %dx%d psm=%s px_size=0x%X' % (w, h, at['psm'], at['px_size']))

    def inkmask(x0, y0, x1, y1):
        x0, y0 = max(0, x0), max(0, y0)
        x1, y1 = min(w, x1), min(h, y1)
        if x1 <= x0 or y1 <= y0:
            return (0, 0, 0, 0, 0)
        n = 0
        bx0, by0, bx1, by1 = 10 ** 9, 10 ** 9, -1, -1
        for y in range(y0, y1):
            row = gray[y * w:y * w + w]
            for x in range(x0, x1):
                if row[x] == 0:
                    n += 1
                    if x < bx0:
                        bx0 = x
                    if x > bx1:
                        bx1 = x
                    if y < by0:
                        by0 = y
                    if y > by1:
                        by1 = y
        return (n, bx0, by0, bx1, by1)

    NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH

    def yrow(r):
        return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))

    # 行数
    rows = []
    r = 0
    while True:
        y = yrow(r)
        if y + CH > h:
            break
        rows.append((r, y))
        r += 1
    print('网格行数 = %d (r=0..%d), 列数 = %d, 标称格 = %d' %
          (len(rows), rows[-1][0], NCOL, len(rows) * NCOL))

    # 逐格墨迹 bbox（格内相对）
    hist_w = Counter()
    hist_h = Counter()
    hist_xy = Counter()
    n_ink_cells = 0
    touch15 = []          # 有墨落在格内 col15 / row15 的格
    per_row = []
    total_ink = 0
    for (r, y) in rows:
        rowinfo = dict(row=r, y=y, ncol_ink=0, maxw=0, maxh=0)
        for c in range(NCOL):
            x0 = CW * c
            n, bx0, by0, bx1, by1 = inkmask(x0, y, x0 + CW, y + CH)
            if n == 0:
                continue
            n_ink_cells += 1
            total_ink += n
            iw = bx1 - x0 + 1
            ih = by1 - y + 1
            rx0, ry0 = bx0 - x0, by0 - y
            hist_w[iw] += 1
            hist_h[ih] += 1
            hist_xy[(iw, ih)] += 1
            rowinfo['ncol_ink'] += 1
            rowinfo['maxw'] = max(rowinfo['maxw'], iw)
            rowinfo['maxh'] = max(rowinfo['maxh'], ih)
            if rx0 + iw - 1 >= CW - 1 or ry0 + ih - 1 >= CH - 1 or rx0 == 0 or ry0 == 0:
                touch15.append((r, c, rx0, ry0, iw, ih))
        per_row.append(rowinfo)

    print('\n有墨的格 = %d (标称 %d)' % (n_ink_cells, len(rows) * NCOL))
    print('墨宽直方 (宽:格数): %s' % dict(sorted(hist_w.items())))
    print('墨高直方 (高:格数): %s' % dict(sorted(hist_h.items())))
    print('最大墨 bbox = %dx%d' % (max(hist_w), max(hist_h)))
    print('墨贴到格边(rel0 或 rel15)的格数 = %d' % len(touch15))
    for t in touch15[:20]:
        print('   row=%d col=%d rel=(%d,%d) %dx%d' % t)
    print('\n逐行: %s' % [(x['row'], x['y'], x['ncol_ink'], x['maxw'], x['maxh'])
                          for x in per_row])

    # EN 带 / 图标窗 / 键盘带
    en = inkmask(0, EN_BAND[0], w, EN_BAND[1])
    ic = inkmask(0, ICON_WIN[0], 66, ICON_WIN[1])
    print('\nEN 带 [%d,%d) 墨 = %d bbox=%s' % (EN_BAND[0], EN_BAND[1], en[0], en[1:]))
    print('图标窗 [%d,%d)x[0,66) 墨 = %d bbox=%s' % (ICON_WIN[0], ICON_WIN[1], ic[0], ic[1:]))
    # 全图零率
    z = sum(1 for v in gray if v != 0)
    print('图集非零 texel = %d / %d (%.1f%%)  墨 texel = %d' % (z, w * h, 100.0 * z / (w * h),
                                                              total_ink))
    rep = dict(atlas=dict(w=w, h=h, psm=at['psm'], px_size=at['px_size']),
               grid=dict(NCOL=NCOL, CW=CW, CH=CH, rows=len(rows), cells=len(rows) * NCOL),
               ink_cells=n_ink_cells, max_ink_w=max(hist_w), max_ink_h=max(hist_h),
               hist_w=dict(sorted(hist_w.items())), hist_h=dict(sorted(hist_h.items())),
               hist_wh={'%dx%d' % k: v for k, v in sorted(hist_xy.items())},
               touch_edge=touch15[:200], n_touch_edge=len(touch15),
               per_row=per_row, en_band_ink=en[0], icon_win_ink=ic[0],
               nonzero_texels=z, ink_texels=total_ink)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    json.dump(rep, open(a.json, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('-> %s' % a.json)


main()
