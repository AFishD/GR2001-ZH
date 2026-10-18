# -*- coding: utf-8 -*-
r"""r71n_hi_frag.py — 高精准度 9 条里含缺字的片段清单 (供 step3.2 最小伤害替换)"""
import csv
import io
import json
import os
import re
import sys
from collections import defaultdict

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
d = json.load(io.open(CS, encoding='utf-8'))
HAVE = set(d['pair_of']) | set(d['codes'])

HI = ['SFXML:T0065', 'SFXML:T0066', 'SFXML:T0063', 'SFXML:T0043', 'SFXML:T0044', 'SFXML:T0046',
      'SFXML:T0047', 'SFXML:T0048', 'SFXML:T0064']

rows = list(csv.DictReader(io.open(os.path.join(HERE, 'r71_reduced_long.csv'),
                                  encoding='utf-8-sig', newline='')))
print('### 高精准度 9 条的缺字片段 (run 口径)')
out = []
for r in rows:
    if r['id'] not in HI:
        continue
    t = r['text_edited'] or ''
    n = len(t)
    i = 0
    while i < n:
        if '\u4e00' <= t[i] <= '\u9fff':
            j = i
            while j < n and '\u4e00' <= t[j] <= '\u9fff':
                j += 1
            run = t[i:j]
            miss = [ch for ch in run if ch not in HAVE]
            if miss:
                ctx = t[max(0, i - 8):i] + '〖' + run + '〗' + t[j:j + 8]
                out.append((r['id'], run, ''.join(sorted(set(miss))), ctx.replace('\n', '\\n')))
            i = j
        else:
            i += 1

cur = None
for eid, run, miss, ctx in out:
    if eid != cur:
        cur = eid
        print('\n===== %s =====' % eid)
    print('  %-30s [%s]' % (run, miss))
    print('        …%s…' % ctx)

with io.open(os.path.join(HERE, 'r71_hi_frag.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for eid, run, miss, ctx in out:
        f.write('%s\t%s\t%s\t%s\n' % (eid, run, miss, ctx))
print('\n合计 %d 个片段 -> r71_hi_frag.txt' % len(out))
