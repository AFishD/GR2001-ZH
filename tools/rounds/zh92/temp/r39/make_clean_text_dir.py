# -*- coding: utf-8 -*-
"""r39: 为「构筑成功路径」验收准备一份干净的注入目录。

只做一件事: 把 GR_ZH92/text 里**可注入**的 *(_text_*).csv 复制到目标目录,
并清空两行**已知缺字形**的 SFXML 条目 (T0012 / T0031) 的 text_edited ——
这两条的原文里有 「延」(U+5EF6), 本盘字库只有死 pair AEFE、图集里没有格子,
所以字库覆盖预检会 (正确地) 拒绝写盘。清空 = 这一条不改动 ⇒ 预检通过。

★ 绝不改 GR_ZH92/text 里的任何文件 (只读 + 复制)。
★ view 表 (_view_*.csv) 一律不复制 —— 它们本来就不该进注入目录。
"""
import csv
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
DST = os.path.join(HERE, 'text_clean')
SKIP_IDS = {'SFXML:T0012', 'SFXML:T0031'}
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST)

for fn in sorted(os.listdir(SRC)):
    if not fn.lower().endswith('.csv') or '_text_' not in fn or '_view_' in fn:
        continue
    sp, dp = os.path.join(SRC, fn), os.path.join(DST, fn)
    with io.open(sp, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.reader(f))
    cols = [c.strip() for c in rows[0]]
    ie = cols.index('text_edited')
    n_clear = 0
    for r in rows[1:]:
        if len(r) > ie and r[0].strip() in SKIP_IDS and r[ie].strip():
            r[ie] = ''
            n_clear += 1
    with io.open(dp, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')
        for r in rows:
            w.writerow(r)
    print('  %-34s %5d 行 (清空 %d)' % (fn, len(rows) - 1, n_clear))
print('⇒ %s' % DST)
