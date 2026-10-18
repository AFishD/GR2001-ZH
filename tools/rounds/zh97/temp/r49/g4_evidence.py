# -*- coding: utf-8 -*-
r"""g4_evidence.py — round49 侦察 (四): 四份"判据证据"。

① 人名到底落在哪: view_character_names.csv 的 has_cjk 分布 + 样例行 (确认盘上已是英文名);
② 144 个死字在 view 表里的每一次出现 (连上下文), 判定"真用字"还是"二进制误码";
③ 引擎视图 col 62/63 (x>=992) 是不是"回绕副本": 与同行 col 0..5 逐像素比对;
④ 那 10 个残墨格的 ASCII 点阵图 (人眼判定: 是碎片还是活图标)。
"""
import csv
import io
import os
import sys
from collections import Counter

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
DEAD = io.open(os.path.join(HERE, 'g3_check.json'), encoding='utf-8').read()
import json                                                          # noqa: E402
DEAD = json.loads(DEAD)['dead']


def main():
    # ---------- ① 人名 ----------
    p = os.path.join(TEXT, 'GR_ZH97_view_character_names.csv')
    cnt = Counter()
    samples = []
    rows = 0
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            rows += 1
            cnt[(row.get('has_cjk') or '?').strip().lower()] += 1
            t = row.get('text') or ''
            if len(samples) < 4000:
                samples.append(t)
    print('=== ① GR_ZH97_view_character_names.csv: %d 行; has_cjk 分布 %s' % (rows, dict(cnt)))
    # 用 charset 解码 "像人名" 的串
    nm = [t for t in samples if t and t[0].isalpha() and 2 < len(t) < 16 and ' ' not in t
          and t.replace('_', '').isalnum()]
    print('  像"名字"的串 %d 个, 前 30: %s' % (len(nm), nm[:30]))
    cjk_rows = []
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if (row.get('has_cjk') or '').strip().lower() == 'yes':
                cjk_rows.append(row)
    print('  has_cjk=yes 的行 %d 条' % len(cjk_rows))
    for row in cjk_rows[:10]:
        print('    %-26s off=%-8s %r' % ((row.get('container') or '')[:26], row.get('offset'),
                                         (row.get('text') or '')[:70]))

    # ---------- ② 死字在 view 表的每次出现 ----------
    print('\n=== ② %d 个死字在 view 表的出现 (含上下文) ===' % len(DEAD))
    tot = 0
    for fn in sorted(os.listdir(TEXT)):
        if '_view_' not in fn or not fn.endswith('.csv') or fn.endswith('containers_summary.csv'):
            continue
        with io.open(os.path.join(TEXT, fn), encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                t = row.get('text') or ''
                hit = [ch for ch in DEAD if ch in t]
                if hit:
                    tot += 1
                    if tot <= 30:
                        i = t.find(hit[0])
                        print('  %-22s %-24s has_cjk=%-4s run=%-2s %r'
                              % (fn.replace('GR_ZH97_view_', ''), (row.get('container') or '')[:24],
                                 row.get('has_cjk'), row.get('cjk_run'),
                                 t[max(0, i - 20):i + 20]))
    print('  合计命中行 %d' % tot)

    # ---------- ③ 回绕副本 ----------
    font = dump_font.load_font(ISO)
    am = font['atlas']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    ink = A.eng
    print('\n=== ③ 引擎视图 col 62/63 (x=992..1023) 是不是"回绕副本"? ===')
    yrow = lambda r: tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))
    for r in range(25):
        y = yrow(r)
        a = ink[y:y + 16, 992:1024]
        if not a.any():
            continue
        best = None
        for half in (0, 1):
            sub = a[:, half * 16:(half + 1) * 16]
            for c in range(62):
                b = ink[y:y + 16, c * 16:c * 16 + 16]
                same = int((sub == b).sum())
                if best is None or same > best[1]:
                    best = (c, same, int(b.sum()), 'col%d' % (62 + half))
        print('  网格行 %2d y=%3d: col62/63 墨=%3d ⇒ 最像 %s(相同像素 %d/256, 该列墨 %d)'
              % (r, y, int(a.sum()), best[3], best[1], best[2]))
    # 也看"引擎行 y 与 y+1 的关系" (低 1 行渗漏)
    print('  (若"完全相同"= 256, 就是逐像素副本)')

    # ---------- ④ 10 格 ASCII 点阵 ----------
    print('\n=== ④ 那 10 个残墨格的 ASCII 点阵 (X=墨, .=空, 顶部带 x 坐标) ===')
    ft = np.zeros((am['h'], am['w']), bool)
    for (_fn, _fld, rs) in font['faces']:
        for (_b0, _b1, u0, v0, u1, v1) in rs:
            if u1 <= u0 or v1 <= v0:
                continue
            ft[max(0, v0 - 2):v1 + 2, max(0, u0 - 4):u1 + 4] = True
    for (r, c) in [(21, 5), (21, 6), (21, 7), (21, 8), (22, 5), (22, 6), (22, 7), (22, 8),
                   (23, 8), (23, 9)]:
        s = r * tcslib.NCOL + c
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        cell = ink[y:y + 16, x:x + 16]
        pro = ft[y:y + 16, x:x + 16]
        print('  --- 网格行 %d col %d  cell=(%d,%d)  墨=%d  (窗口内墨=%d / 窗口外=%d)'
              % (r, c, x, y, int(cell.sum()), int((cell & pro).sum()), int((cell & ~pro).sum())))
        for yy in range(16):
            line = ''.join('X' if cell[yy, xx] else ('o' if pro[yy, xx] else '.') for xx in range(16))
            print('      %s' % line)
        print('      (o = FT 采样窗(膨胀±4,2) 覆盖; X = 墨; . = 空)')


if __name__ == '__main__':
    main()
