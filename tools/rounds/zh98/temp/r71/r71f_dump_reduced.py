# -*- coding: utf-8 -*-
r"""r71f_dump_reduced.py — 把 GR_ZH113(现役缩减版, 0 缺字) 的 16 条正文 + 高精准度条目导出, 作为命名/术语参考"""
import csv
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text', 'GR_ZH113_text_long.csv')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LOW = ['SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'] + ['SFXML:T%04d' % i for i in range(50, 63)]
HI = ['SFXML:T0065', 'SFXML:T0066', 'SFXML:T0063', 'SFXML:T0043', 'SFXML:T0044', 'SFXML:T0046',
      'SFXML:T0047', 'SFXML:T0048', 'SFXML:T0064']

rows = {r['id']: r for r in csv.DictReader(io.open(SRC, encoding='utf-8-sig', newline=''))}

with io.open(os.path.join(HERE, 'r71_reduced_16.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for eid in LOW:
        r = rows[eid]
        f.write('=' * 96 + '\n### %s  (GR_ZH113 缩减版, 0 缺字)\n' % eid)
        f.write((r['text_zh'] or '').replace('\n', '\\n\n') + '\n\n')

with io.open(os.path.join(HERE, 'r71_hi_entries.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for eid in HI:
        r = rows[eid]
        f.write('=' * 96 + '\n### %s\n' % eid)
        f.write((r['text_en'] or '') + '\n---- 中文(缩减版) ----\n')
        f.write((r['text_zh'] or '') + '\n\n')
print('-> r71_reduced_16.txt / r71_hi_entries.txt')
