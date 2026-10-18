# -*- coding: utf-8 -*-
r"""g1_geom.py — round49 侦察: 把"引擎到底会采样图集里的哪些像素"算到可复现。

只读, 不写盘。输出:
  · 容器分段表 (TRXPOS 行) / 图集墨总量;
  · FT 记录矩形 (3 face) 的 v0 直方图与"从不被采样的 y 带";
  · 引擎网格 25 行 x 62 列 + 4 类"网格外区域"的墨分布;
  · charset 空槽里有墨的那些 (报告里说的 "92") 逐格拆解:
      ink 总量 / FT 窗内 ink / 窗外 ink / 是否是禁用格;
  · 逐字用量 (注入表 / view 表分开数)。
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


def main():
    font = dump_font.load_font(ISO)
    am, faces = font['atlas'], font['faces']
    W, H, PSM = am['w'], am['h'], am['psm']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], W, H, PSM)
    ink = A.eng
    cs = tcslib.Charset()
    print('图集 %dx%d psm=0x%02X  容器 %d B  段 %d 个' % (W, H, PSM, am['px_size'], len(A.segs)))
    print('段 (首行, 数据偏移, 字节数): %s' % [(a, b, c) for a, b, c in A.segs])
    print('墨总量 %d' % int(ink.sum()))
    print()

    # ---- FT 记录矩形 ----
    protect, rects = repack_font.protect_mask(faces, W, H)
    print('FT 记录矩形 (非空): %d 条; 覆盖像素 %d' % (len(rects), int(protect.sum())))
    v0s = {}
    for r in rects:
        v0s[r['v0']] = v0s.get(r['v0'], 0) + 1
    print('v0 直方图 (顶边 y: 条数): %s' % dict(sorted(v0s.items())))
    u0s = {}
    for r in rects:
        u0s[(r['v0'], r['face'])] = u0s.get((r['v0'], r['face']), 0) + 1
    print('(v0, face) 计数: %s' % dict(sorted(u0s.items())))
    # 逐 face 的矩形数
    for (fn, fld, rs) in faces:
        ne = sum(1 for r in rs if r[4] > r[2] and r[5] > r[3])
        print('  face %-8s nrec=%d 非空=%d fld[4..5]=%s' % (fn, len(rs), ne, fld[4:6]))
    print()

    # ---- 引擎网格 ----
    yrow = lambda r: tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))
    cap = tcslib.pair_capacity()
    used_in = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            used_in[tcslib.pair_slot(b1, b2)] = ch
    print('charset: 对偶 %d (合法 lead 的 %d), 单字节 %d, 容量 %d'
          % (len(cs.enc_pair), len(used_in), len(cs.enc_single), cap))
    free = [s for s in range(cap) if s not in used_in]
    print('空槽 %d' % len(free))

    rec_cells = set(tcslib.ATLAS_ENGINE_SINGLE_CELLS)
    rows_info = {}
    for s in free:
        r, c = s // tcslib.NCOL, s % tcslib.NCOL
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        cell = ink[y:y + 16, x:x + 16]
        ft = protect[y:y + 16, x:x + 16]
        rows_info[s] = dict(r=r, c=c, x=x, y=y, n=int(cell.sum()),
                            n_ft=int((cell & ft).sum()), n_out=int((cell & ~ft).sum()),
                            rec=bool((r, c) in rec_cells))
    inked = [s for s in free if rows_info[s]['n'] > 0]
    print('空槽里有墨的 = %d (报告里的 "需回收")' % len(inked))
    n_out = [s for s in inked if rows_info[s]['n_out'] > 0]
    print('  其中"FT 窗之外还有墨"的 = %d' % len(n_out))
    if n_out:
        for s in n_out[:40]:
            d = rows_info[s]
            print('    slot=%4d row=%2d col=%2d y=%3d ink=%3d FT内=%3d FT外=%3d 禁用格=%s'
                  % (s, d['r'], d['c'], d['y'], d['n'], d['n_ft'], d['n_out'], d['rec']))
    rec_cnt = sum(1 for s in inked if rows_info[s]['rec'])
    print('  其中禁用格(整格被记录码占) = %d; 其余 = %d (靠 FT 矩形保护)'
          % (rec_cnt, len(inked) - rec_cnt))
    print('  空槽里有墨、且一格墨都不在 FT 窗内的 = %d'
          % len([s for s in inked if rows_info[s]['n_ft'] == 0]))
    print()

    # ---- 网格外区域 ----
    print('=== 网格外区域 (引擎对偶格公式永不覆盖) ===')
    regions = [
        ('顶部 2 行 y=0..1', 0, 2, 0, W),
        ('行 11 与行 12 之间的 3 行空洞 y=194..241', 194, 242, 0, W),
        ('网格下方 y=450..511', 450, H, 0, W),
        ('右侧 2 格 x=992..1023 (网格行带内)', yrow(0), yrow(24) + 16, 992, W),
    ]
    for (nm, y0, y1, x0, x1) in regions:
        sub = ink[y0:y1, x0:x1]
        ft = protect[y0:y1, x0:x1]
        print('  %-42s 区域 %d px, 墨 %d, 其中 FT 窗内 %d, 窗外 %d'
              % (nm, sub.size, int(sub.sum()), int((sub & ft).sum()), int((sub & ~ft).sum())))
    # 逐行细看右侧两格
    print('  右侧 2 格逐网格行:')
    for r in range(25):
        y = yrow(r)
        sub = ink[y:y + 16, 992:1024]
        ft = protect[y:y + 16, 992:1024]
        if sub.any():
            print('    网格行 %2d y=%3d 墨 %3d (FT 内 %d)'
                  % (r, y, int(sub.sum()), int((sub & ft).sum())))
    # y=194..241 逐行
    print('  空洞带 y=194..241 逐行墨:')
    for y in range(194, 242):
        n = int(ink[y, :].sum())
        ftn = int((ink[y, :] & protect[y, :]).sum())
        if n:
            print('    y=%3d 墨 %4d (FT 内 %d)' % (y, n, ftn))
    # y>=450
    print('  y>=450 逐行墨:')
    for y in range(450, H):
        n = int(ink[y, :].sum())
        ftn = int((ink[y, :] & protect[y, :]).sum())
        if n:
            print('    y=%3d 墨 %4d (FT 内 %d)' % (y, n, ftn))
    print()

    # ---- 逐字用量 ----
    counts, where = {}, {}
    files_inj, files_view = [], []
    for fn in sorted(os.listdir(TEXT)):
        if not fn.endswith('.csv') or '_text_' not in fn and '_view_' not in fn:
            continue
        (files_inj if '_text_' in fn else files_view).append(fn)
    print('注入表: %s' % files_inj)
    print('view 表: %s (%d 张)' % (files_view[:3], len(files_view)))
    for fn in files_inj:
        with io.open(os.path.join(TEXT, fn), encoding='utf-8-sig', newline='') as f:
            for i, row in enumerate(csv.reader(f)):
                if i == 0:
                    continue
                for cell in row:
                    for ch in cell:
                        counts[ch] = counts.get(ch, 0) + 1
                        where.setdefault(ch, []).append('%s:r%d' % (fn.split('_text_')[1][:-4], i))
    vcounts = {}
    vcjk = {}
    for fn in files_view:
        with io.open(os.path.join(TEXT, fn), encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            for row in rd:
                txt = row.get('text') or ''
                hc = (row.get('has_cjk') or '').strip().lower()
                for ch in txt:
                    vcounts[ch] = vcounts.get(ch, 0) + 1
                    if hc == 'yes':
                        vcjk[ch] = vcjk.get(ch, 0) + 1
    cand = '珍琳费贾赖辉辛迈郑闫阮阳陈隆雅韦魏鲍鹏麦'
    print()
    print('=== 20 个人名字的用量 ===')
    for ch in cand:
        p = cs.enc_pair.get(ch)
        slot = tcslib.pair_slot(*p) if p else None
        print('  %s pair=%s slot=%s 注入表 %d 次 | view 表 %d 次 (has_cjk=yes 行 %d 次)'
              % (ch, p, slot, counts.get(ch, 0), vcounts.get(ch, 0), vcjk.get(ch, 0)))
    print()
    print('=== charset 里"注入表 0 次"的字 (死字嫌疑) ===')
    dead = [ch for ch in cs.enc_pair if counts.get(ch, 0) == 0]
    print('共 %d 个: %s' % (len(dead), ''.join(sorted(dead))))
    print()
    print('=== 这些死字在 view 表里的出现 (可能只是误码) ===')
    for ch in sorted(dead):
        if vcounts.get(ch, 0):
            print('  %s: view %d 次 (has_cjk=yes 行 %d 次)' % (ch, vcounts[ch], vcjk.get(ch, 0)))
    print()
    print('=== view 表里 has_cjk=yes 行中出现的 charset 字 (真正的"码位锁定"嫌疑) ===')
    lock = sorted([ch for ch in vcjk if vcjk[ch] > 0 and ch in cs.enc_pair])
    print('共 %d 个: %s' % (len(lock), ''.join(lock)))
    out = dict(iso=ISO, atlas_ink=int(ink.sum()), ft_rects=len(rects),
               free=len(free), free_inked=len(inked),
               free_inked_ft_outside=len(n_out), free_inked_rec=rec_cnt,
               dead_inject=len(dead), dead_chars=''.join(sorted(dead)),
               view_cjk_locked=''.join(lock),
               counts=counts, vcounts=vcounts, vcjk=vcjk)
    io.open(os.path.join(HERE, 'g1_geom.json'), 'w', encoding='utf-8', newline='\n').write(
        json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('\n-> g1_geom.json')


if __name__ == '__main__':
    main()
