# -*- coding: utf-8 -*-
r"""g3_check.py — round49 侦察 (三): 死字复核 + 残墨像素级集合。

① 20 个人名字 / 144 个"注入表 0 次"候选字: 逐表逐一词复核 (含 text_en / note 等所有列);
② view 表里 has_cjk=yes 且 cjk_run >= 3 的行 (真的像中文?) —— 判定"码位锁定"风险;
③ 残墨像素级集合 = 墨 ∧ ¬(已用对偶格) ∧ ¬(全部 FT 采样窗膨胀±(4,2)), 并分区域统计。
"""
import csv
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402
import repack_font                                                   # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
TEXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'text')
W, H = 1024, 512
TX, TY = tcslib.GLYPH_TOL_X, tcslib.GLYPH_TOL_Y
CAND20 = '珍琳费贾赖辉辛迈郑闫阮阳陈隆雅韦魏鲍鹏麦'


def main():
    font = dump_font.load_font(ISO)
    am, faces = font['atlas'], font['faces']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    ink = A.eng
    cs = tcslib.Charset()

    # ---------- ① 用量 ----------
    inj_files = [f for f in sorted(os.listdir(TEXT)) if f.endswith('.csv') and '_text_' in f]
    view_files = [f for f in sorted(os.listdir(TEXT)) if f.endswith('.csv') and '_view_' in f]
    counts, hits = {}, {}
    for fn in inj_files:
        with io.open(os.path.join(TEXT, fn), encoding='utf-8-sig', newline='') as f:
            rd = csv.reader(f)
            head = next(rd)
            for i, row in enumerate(rd, start=1):
                for ci, cell in enumerate(row):
                    for ch in cell:
                        counts[ch] = counts.get(ch, 0) + 1
                        if len(hits.get(ch, [])) < 4:
                            hits.setdefault(ch, []).append('%s#r%d.%s' % (fn.split('_text_')[1][:-4], i, head[ci] if ci < len(head) else ci))
    print('注入表 %d 张, 不同字符 %d 个' % (len(inj_files), len(counts)))
    dead = sorted([ch for ch in cs.enc_pair if counts.get(ch, 0) == 0])
    print('charset 对偶字里"注入表 0 次"的: %d 个' % len(dead))
    print(''.join(dead))
    print('\n20 个点名的人名字是否都在这张清单里: %s'
          % all(ch in dead for ch in CAND20))
    for ch in CAND20:
        print('  %s: 注入表 %d 次' % (ch, counts.get(ch, 0)))

    # ---------- ② view 表真中文 ----------
    print('\n=== view 表 has_cjk=yes 且 cjk_run>=3 的行 ===')
    n_hit = 0
    for fn in view_files:
        with io.open(os.path.join(TEXT, fn), encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                tc_ = (row.get('has_cjk') or '').strip().lower()
                try:
                    run = int(row.get('cjk_run') or 0)
                except ValueError:
                    run = 0
                if tc_ == 'yes' and run >= 3:
                    n_hit += 1
                    if n_hit <= 25:
                        print('  %-26s %-26s run=%d off=%-8s %r'
                              % (fn.replace('GR_ZH97_view_', ''), (row.get('container') or '')[:26],
                                 run, row.get('offset'), (row.get('text') or '')[:64]))
    print('  合计 %d 行' % n_hit)

    # ---------- ③ 残墨像素 ----------
    lut_used = np.zeros((H, W), bool)
    for ch, (b1, b2) in cs.enc_pair.items():
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(b1, b2))
        lut_used[y:y + 16, x:x + 16] = True
    ft = np.zeros((H, W), bool)
    for (_fn, _fld, rs) in faces:
        for (_b0, _b1, u0, v0, u1, v1) in rs:
            if u1 <= u0 or v1 <= v0:
                continue
            a0, b0 = max(0, u0 - TX), max(0, v0 - TY)
            a1, b1 = min(W, u1 + TX), min(H, v1 + TY)
            ft[b0:b1, a0:a1] = True
    residue = ink & ~lut_used & ~ft
    print('\n=== 残墨像素 (墨 ∧ ¬已用对偶格 ∧ ¬FT 膨胀窗) ===')
    print('墨总量 %d; 已用格 %d px; FT 膨胀窗 %d px; **残墨 %d px**'
          % (int(ink.sum()), int(lut_used.sum()), int(ft.sum()), int(residue.sum())))

    # 分区域
    pair = np.zeros((H, W), bool)
    for s in range(tcslib.pair_capacity()):
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        pair[y:y + 16, x:x + 16] = True
    reg = {}
    reg['自由对偶格内 (空槽)'] = residue & pair
    reg['记录码禁用格内'] = np.zeros((H, W), bool)
    for (r, c) in tcslib.ATLAS_ENGINE_SINGLE_CELLS:
        x, y = tcslib.atlas_cell_xy_engine_view(r * tcslib.NCOL + c)
        reg['记录码禁用格内'][y:y + 16, x:x + 16] = True
    reg['记录码禁用格内'] &= residue
    reg['右侧 x>=992'] = residue.copy(); reg['右侧 x>=992'][:, :992] = False
    reg['顶部 y<2'] = residue.copy(); reg['顶部 y<2'][2:, :] = False
    reg['空洞 y=194..241'] = residue.copy(); reg['空洞 y=194..241'][:194, :] = False; reg['空洞 y=194..241'][242:, :] = False
    reg['网格下方 y>=450'] = residue.copy(); reg['网格下方 y>=450'][:450, :] = False
    rest = residue.copy()
    for m in reg.values():
        rest &= ~m
    reg['其它'] = rest
    for k, m in reg.items():
        print('  %-22s %5d px' % (k, int(m.sum())))
    # 空槽格逐个
    print('\n  自由对偶格(空槽)里有残墨的格:')
    rows = []
    for s in range(tcslib.pair_capacity()):
        if s in [tcslib.pair_slot(*p) for p in cs.enc_pair.values()
                 if tcslib.PAIR_LEAD_LO <= p[0] < tcslib.PAIR_LEAD_HI]:
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        n = int(residue[y:y + 16, x:x + 16].sum())
        if n:
            rows.append((s, s // 62, s % 62, x, y, n))
    for (s, r, c, x, y, n) in rows:
        print('    slot=%4d row=%2d col=%2d cell=(%d,%d) 残墨 %3d px' % (s, r, c, x, y, n))
    # 记录码禁用格
    print('\n  记录码禁用格里有残墨的格:')
    for (r, c) in sorted(tcslib.ATLAS_ENGINE_SINGLE_CELLS):
        x, y = tcslib.atlas_cell_xy_engine_view(r * tcslib.NCOL + c)
        n = int(residue[y:y + 16, x:x + 16].sum())
        if n:
            print('    row=%2d col=%2d cell=(%d,%d) 残墨 %3d px  (%s)'
                  % (r, c, x, y, n, tcslib.ATLAS_ENGINE_SINGLE_CELLS[(r, c)]))
    # 非格区域的残墨 (逐 16x16 tile 汇总, 便于报告)
    print('\n  格外的残墨 (按 16x16 tile, 只列有墨的):')
    tiles = []
    for ty in range(0, H, 16):
        for tx_ in range(0, W, 16):
            n = int(residue[ty:ty + 16, tx_:tx_ + 16].sum())
            if n:
                tiles.append((tx_ // 16, ty // 16, tx_, ty, n))
    for t in tiles:
        print('    tile col=%2d row=%2d (%4d,%3d) 残墨 %3d' % t)
    io.open(os.path.join(HERE, 'g3_check.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(dict(dead=dead, counts={k: v for k, v in counts.items() if k in dead},
                        residue_px=int(residue.sum()),
                        residue_by_region={k: int(v.sum()) for k, v in reg.items()},
                        tiles=[list(t) for t in tiles], inj_files=inj_files,
                        view_cjk_run3=n_hit), ensure_ascii=False, indent=1) + '\n')
    print('\n-> g3_check.json')


if __name__ == '__main__':
    main()
