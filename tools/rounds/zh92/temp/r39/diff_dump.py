# -*- coding: utf-8 -*-
"""r39: 对比「现役盘已提交的表」与「本次重 dump 的表」—— 确认我的改动没有改语义。只读。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
A = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
B = os.path.join(HERE, 'repro')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def load(p):
    with io.open(p, 'r', encoding='utf-8-sig', newline='') as f:
        rd = csv.DictReader(f)
        return list(rd), rd.fieldnames


for kind in ('long', 'long_nowrap', 'short'):
    pa = os.path.join(A, 'GR_ZH92_text_%s.csv' % kind)
    pb = os.path.join(B, 'P_text_%s.csv' % kind)
    ra, ca = load(pa)
    rb, cb = load(pb)
    print('\n== %-12s 已提交 %5d 行 / 新 dump %5d 行; 列相同=%s =='
          % (kind, len(ra), len(rb), ca == cb))
    da = dict((r['id'], r) for r in ra)
    db = dict((r['id'], r) for r in rb)
    only_a = sorted(set(da) - set(db))
    only_b = sorted(set(db) - set(da))
    if only_a:
        print('   只在旧表: %s' % ' '.join(only_a[:8]))
    if only_b:
        print('   只在新表: %s' % ' '.join(only_b[:8]))
    n_diff = 0
    bycol = {}
    samples = []
    for rid in sorted(set(da) & set(db)):
        x, y = da[rid], db[rid]
        if x == y:
            continue
        n_diff += 1
        for c in ca:
            if (x.get(c) or '') != (y.get(c) or ''):
                bycol[c] = bycol.get(c, 0) + 1
                if len(samples) < 6:
                    samples.append((rid, c, x.get(c), y.get(c)))
    print('   内容不同的行 %d; 差异按列: %s' % (n_diff, bycol))
    for (rid, c, x, y) in samples:
        print('      %-16s %-12s 旧=%r' % (rid, c, (x or '')[:60]))
        print('      %-16s %-12s 新=%r' % ('', '', (y or '')[:60]))
