# -*- coding: utf-8 -*-
r"""m8_find_zhong.py — round47 ⑧: 在文本表里找 中/抖, 定位它们所在的长文条目 (决定实机导航)。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'text')

for n in sorted(os.listdir(TXT)):
    if not n.endswith('.csv'):
        continue
    rows = list(csv.DictReader(io.open(os.path.join(TXT, n), encoding='utf-8-sig')))
    hits = [r for r in rows if '中' in r['text_edited'] or '抖' in r['text_edited']]
    print('=' * 78)
    print('%s : %d 行含 中/抖 (总 %d 行)' % (n, len(hits), len(rows)))
    for r in hits[:60]:
        t = r['text_edited']
        for ch in ('中', '抖'):
            i = t.find(ch)
            while i >= 0:
                print('   [%s] id=%s %s: …%s…' % (ch, r['id'],
                      {k: r[k] for k in r if k not in ('text_edited', 'text_original')
                       and len(r[k] or '') < 40},
                      t[max(0, i - 20):i + 20].replace('\n', '⏎')))
                i = t.find(ch, i + 1)
