# -*- coding: utf-8 -*-
r"""r71ad_shortdiff.py — final: short 表逐列对比 (只应 max_bytes 变)"""
import csv
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
A = os.path.join(REPO, 'work/builds/GR_ZH113/text')
B = os.path.join(REPO, 'work/builds/GR_ZH113b/text')
for kind in ('long_nowrap', 'short'):
    pa = os.path.join(A, 'GR_ZH113_text_%s.csv' % kind)
    pb = os.path.join(B, 'GR_ZH113_B_text_%s.csv' % kind)
    ra = {r['id']: r for r in csv.DictReader(io.open(pa, encoding='utf-8-sig', newline=''))}
    rb = {r['id']: r for r in csv.DictReader(io.open(pb, encoding='utf-8-sig', newline=''))}
    cols, rows = {}, []
    for i in ra:
        d = [c for c in ra[i] if ra[i][c] != rb[i][c]]
        if d:
            rows.append(i)
            for c in d:
                cols[c] = cols.get(c, 0) + 1
    print('== %-12s 行数 %d/%d  不同行 %d  变化列: %s' % (kind, len(ra), len(rb), len(rows), cols))
    for i in rows[:3]:
        for c in ra[i]:
            if ra[i][c] != rb[i][c]:
                print('     %s.%s: %s -> %s' % (i, c, ra[i][c], rb[i][c]))
