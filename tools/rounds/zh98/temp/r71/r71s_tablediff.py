# -*- coding: utf-8 -*-
r"""r71s_tablediff.py — 逐列对比两版文本表 (找出到底哪一列变了)"""
import csv
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
A = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text')
B = os.path.join(REPO, 'work', 'builds', 'GR_ZH113_B', 'text')
for kind in ('long', 'long_nowrap', 'short'):
    pa = os.path.join(A, 'GR_ZH113_text_%s.csv' % kind)
    pb = os.path.join(B, 'GR_ZH113_B_text_%s.csv' % kind)
    ra = {r['id']: r for r in csv.DictReader(io.open(pa, encoding='utf-8-sig', newline=''))}
    rb = {r['id']: r for r in csv.DictReader(io.open(pb, encoding='utf-8-sig', newline=''))}
    col_diff = {}
    rows_diff = []
    for i in ra:
        if i not in rb:
            rows_diff.append(i + '(缺)')
            continue
        d = [c for c in ra[i] if ra[i][c] != rb[i][c]]
        if d:
            rows_diff.append(i)
            for c in d:
                col_diff[c] = col_diff.get(c, 0) + 1
    print('== %-12s 行数 %d/%d  不同行 %d  变化列: %s'
          % (kind, len(ra), len(rb), len(rows_diff), col_diff))
    # 抽样看一个变化
    for i in rows_diff[:2]:
        if i in rb:
            for c in ra[i]:
                if ra[i][c] != rb[i][c]:
                    print('     %s.%s:\n        A=%r\n        B=%r' % (i, c, ra[i][c][:120], rb[i][c][:120]))
