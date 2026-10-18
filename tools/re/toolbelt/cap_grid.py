# -*- coding: utf-8 -*-
r"""cap_grid.py -- round73 字库扩容裁决：「改格距」这条杠杆的全部数字。

只读。两件事：
  A 实测: 现役盘上「引擎格位」与「字形实际墨迹」的偏差 (定标 +4 绘制原点的真实含义,
          并给出列数的真实上限).
  B 解析: 参数化的 (W, CW, CH, Y0, SKIP_ROW, SKIP_ROWS) → 可用格数 / 与 EN 带和图标窗的冲突 /
          16px 字形的适配代价.

用法: python tools/re/toolbelt/cap_grid.py [--iso PATH] [--json OUT]
"""
import argparse
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import dump_font as D          # noqa: E402
import tcslib                  # noqa: E402

DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')

EN_BAND = (452, 468)           # 盘上 FT ASCII 记录实测 v0/v1 (FONT_CURRENT_STATE §一)
ICON_WIN = (198, 222)          # DrawString 硬编码图标 UV: (1,198)-(21,218)/(25,198)-(45,218)
DRAW_BIAS_U = 4                # PROGRESS §10: 16px/PSMT4 采样 = 结果 u + 4
CUR = dict(W=1024, H=512, CW=16, CH=16, Y0=2, SKIP_ROW=12, SKIP_ROWS=3)


# ------------------------------------------------------------------ part A

def part_a(iso):
    g = D.load_font(iso)
    at = g['atlas']
    w, h = at['w'], at['h']
    gray = D.atlas_gray(at, view='engine')
    cs = tcslib.Charset()

    def ink(x0, y0, x1, y1):
        n = 0
        for y in range(max(0, y0), min(h, y1)):
            row = gray[y * w: y * w + w]
            n += sum(1 for x in range(max(0, x0), min(w, x1)) if row[x] == 0)
        return n

    def colprof(y0, y1):
        prof = [0] * w
        for y in range(y0, min(h, y1)):
            row = gray[y * w: y * w + w]
            for x in range(w):
                if row[x] == 0:
                    prof[x] += 1
        return prof

    def analyse_row(row):
        y = tcslib.GRID_Y0 + tcslib.CH * (row + (tcslib.GRID_SKIP_ROWS if row >= tcslib.GRID_SKIP_ROW else 0))
        p = colprof(y, y + tcslib.CH)
        blanks = [x for x in range(w) if p[x] == 0]
        # blank runs
        runs = []
        s = None
        for x in range(w):
            if p[x] == 0:
                if s is None:
                    s = x
            else:
                if s is not None:
                    runs.append([s, x - 1, x - s])
                    s = None
        if s is not None:
            runs.append([s, w - 1, w - s])
        # glyph left edges = blank -> ink transitions
        edges = [x for x in range(1, w) if p[x - 1] == 0 and p[x] > 0]
        phase = sorted(set(e % tcslib.CW for e in edges))
        # ink bbox per nominal cell (strict, inside the cell only)
        per_cell = []
        for c in range(tcslib.NCOL):
            x0 = tcslib.CW * c
            xs = [x - x0 for x in range(x0, min(w, x0 + tcslib.CW)) if p[x] > 0]
            per_cell.append([min(xs), max(xs)] if xs else None)
        filled = [c for c in range(tcslib.NCOL) if per_cell[c]]
        return dict(row=row, y=y, band=[y, y + tcslib.CH],
                    blank_cols=len(blanks), blank_runs=runs[:12],
                    n_blank_runs=len(runs),
                    first_ink_x=next((x for x in range(w) if p[x] > 0), None),
                    last_ink_x=next((x for x in range(w - 1, -1, -1) if p[x] > 0), None),
                    left_edge_mod_CW=phase, n_edges=len(edges),
                    filled_cells=len(filled), first_filled=min(filled) if filled else None,
                    last_filled=max(filled) if filled else None,
                    bbox_in_cell_hist=_hist([tuple(per_cell[c]) for c in filled if per_cell[c]]))

    def _hist(items):
        d = {}
        for it in items:
            d[str(list(it))] = d.get(str(list(it)), 0) + 1
        return dict(sorted(d.items(), key=lambda kv: -kv[1])[:12])

    rows_probe = [0, 1, 2, 3, 11, 12, 15, 20, 24, 27]
    return dict(atlas=dict(w=w, h=h, psm=at['psm'], px_size=at['px_size']),
                en_band_ink=ink(0, EN_BAND[0], w, EN_BAND[1]),
                icon_window_ink=ink(0, ICON_WIN[0], 66, ICON_WIN[1]),
                rows=[analyse_row(r) for r in rows_probe])


# ------------------------------------------------------------------ part B

def yrow(r, Y0, CH, SKIP_ROW, SKIP_ROWS):
    return Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))


def eval_cfg(W, H, CW, CH, Y0, SKIP_ROW, SKIP_ROWS, ncol):
    rows = []
    r = 0
    while True:
        y = yrow(r, Y0, CH, SKIP_ROW, SKIP_ROWS)
        if y + CH > H:
            break
        rows.append((r, y))
        r += 1
        if r > 400:
            break
    hole = (Y0 + CH * SKIP_ROW, Y0 + CH * (SKIP_ROW + SKIP_ROWS))
    blocked = [(r, y) for (r, y) in rows if not (y + CH <= EN_BAND[0] or y >= EN_BAND[1])]
    usable = [(r, y) for (r, y) in rows if (r, y) not in blocked]
    return dict(ncol=ncol, nrows=len(rows), max_row=rows[-1][0] if rows else None,
                hole=list(hole), hole_covers_icon=(hole[0] <= ICON_WIN[0] and hole[1] >= ICON_WIN[1]),
                rows_blocked_by_en_band=[r for (r, _) in blocked],
                usable_rows=len(usable),
                cells=len(usable) * ncol,
                max_sampled_x=ncol * CW,
                fits_W=ncol * CW <= W,
                glyph16_stretch=[round(16.0 / CW, 3), round(16.0 / CH, 3)],
                glyph16_fits_1to1=(CW >= 16 and CH >= 16))


def best_skip(W, H, CW, CH, Y0):
    """pick (SKIP_ROW, SKIP_ROWS) that covers the icon window and maximises usable rows."""
    best = None
    for sr in range(1, 40):
        for sn in range(1, 7):
            hole = (Y0 + CH * sr, Y0 + CH * (sr + sn))
            if not (hole[0] <= ICON_WIN[0] and hole[1] >= ICON_WIN[1]):
                continue
            ncol = W // CW
            e = eval_cfg(W, H, CW, CH, Y0, sr, sn, ncol)
            if best is None or e['cells'] > best[0]['cells']:
                best = (e, sr, sn)
    return best


def part_b():
    out = []
    # 基线 = 一行不改 (现役常量) 作对照
    base = eval_cfg(1024, 512, 16, 16, 2, 12, 3, 62)
    base.update(CW=16, CH=16, SKIP_ROW=12, SKIP_ROWS=3, cols_geometric_max=64,
                cols_current_style_margin=62, cells_with_margin=base['cells'],
                baseline=True)
    out.append(base)
    for CW in (16, 15, 14, 13, 12):
        for CH in (16, 15, 14, 13, 12):
            b = best_skip(1024, 512, CW, CH, 2)
            if not b:
                continue
            e, sr, sn = b
            e['CW'], e['CH'], e['SKIP_ROW'], e['SKIP_ROWS'] = CW, CH, sr, sn
            e['cols_geometric_max'] = 1024 // CW
            e['cols_current_style_margin'] = 1024 // CW - 2
            e['cells_with_margin'] = e['usable_rows'] * e['cols_current_style_margin']
            out.append(e)
    out.sort(key=lambda x: -x['cells'])
    return out


def reach():
    """要多少格: 各条编码杠杆下的 pair 码位总数."""
    return dict(
        today=dict(pair_codes=1504, note='gate=0xB1, 16 leads x 94'),
        gate_to_B5=dict(pair_codes=20 * 94, note='gate 0xB1->0xB5: 20 leads x 94'),
        gate_to_B5_net=dict(pair_codes=20 * 94 - 3 - 1,
                            note='扣 3 个被吃的单字节汉字 + 1 个图标码'),
        trail_to_40=dict(pair_codes=16 * 191, note='trail 0xA1->0x40, stride 94->191, gate 0xB1'),
        trail_to_40_and_B5=dict(pair_codes=20 * 191, note='两条都上'),
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=DEFAULT_ISO)
    ap.add_argument('--json', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH98',
                                                   'temp', 'r75', 'grid.json'))
    a = ap.parse_args()
    rep = dict(iso=a.iso, current=CUR, draw_bias_u=DRAW_BIAS_U,
               en_band=EN_BAND, icon_window=ICON_WIN,
               partA_measured=part_a(a.iso),
               partB_capacity=part_b(),
               reach=reach())
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, 'w', encoding='utf-8') as f:
        json.dump(rep, f, indent=1, ensure_ascii=False)
    print('== A 实测(现役盘) ==')
    print(json.dumps(rep['partA_measured'], indent=1, ensure_ascii=False))
    print('== B 解析: (CW,CH) -> 可用格 ==')
    for e in rep['partB_capacity']:
        print('CW=%2d CH=%2d skip=%2d+%d ncol=%2d rows=%2d(EN挡%s) usable_rows=%2d '
              'cells=%4d cells_margin=%4d maxX=%4d fitsW=%s stretch=%s'
              % (e['CW'], e['CH'], e['SKIP_ROW'], e['SKIP_ROWS'], e['ncol'], e['nrows'],
                 e['rows_blocked_by_en_band'], e['usable_rows'], e['cells'],
                 e['cells_with_margin'], e['max_sampled_x'], e['fits_W'],
                 e['glyph16_stretch']))
    print('== 目标格数 ==')
    print(json.dumps(rep['reach'], indent=1, ensure_ascii=False))


main()
