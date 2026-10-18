# -*- coding: utf-8 -*-
"""widths_r68.py — 打印待确认建议的精确宽度 (tcslib.strlen 口径), 供报告引用."""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                               # noqa: E402

with io.open(os.path.join(HERE, 'titles_review.csv'), 'r',
             encoding='utf-8-sig', newline='') as f:
    rows = list(csv.DictReader(f))
print('%-13s %-26s %-28s %5s %5s %6s' % ('id', 'now', 'suggest', 'oldchars', 'newchars', 'dpx'))
for r in rows:
    if r['text_zh'] == r['suggest']:
        continue
    if r['verdict'] in ('结构键不该译',):
        continue
    wo, wn = T.strlen(r['text_zh']), T.strlen(r['suggest'])
    print('%-13s %-26s %-28s %5d %5d %+6d' % (r['id'], r['text_zh'], r['suggest'],
                                              len(r['text_zh']), len(r['suggest']), wn - wo))
