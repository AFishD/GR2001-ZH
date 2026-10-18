# -*- coding: utf-8 -*-
"""看 view 表里"binary_assets 有 1197 条中文"到底是什么 (只读)。"""
import csv
import io
import os
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'text', 'GR_ZH105_view_binary_assets.csv')
print('列头:', end=' ')
with io.open(P, encoding='utf-8-sig', newline='') as f:
    rd = csv.DictReader(f)
    print(rd.fieldnames)
    rows = list(rd)
print('行数', len(rows))

CJK = lambda s: sum(1 for c in s if '\u4e00' <= c <= '\u9fff')
cjk_rows = [r for r in rows if any(CJK(v or '') for v in r.values())]
print('含中文的行: %d' % len(cjk_rows))
byk = {}
for r in cjk_rows:
    byk.setdefault(r.get('kind', '?'), []).append(r)
print('按 kind:', {k: len(v) for k, v in byk.items()})
for r in cjk_rows[:15]:
    print('  %-10s %-34s %r' % (r.get('kind'), (r.get('container') or '')[:34],
                                (r.get('text') or '')[:70]))
# 各 view 表的中文统计
for fn in sorted(os.listdir(os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'text'))):
    if '_view_' not in fn or not fn.endswith('.csv'):
        continue
    p = os.path.join(REPO, 'work', 'builds', 'GR_ZH105', 'text', fn)
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        n = 0
        tot = 0
        for r in rd:
            tot += 1
            if any(CJK(v or '') >= 4 for v in r.values()):
                n += 1
    print('%-42s 行 %6d  含≥4连续中文 %5d' % (fn, tot, n))
