# -*- coding: utf-8 -*-
r"""p24_find_entry.py — round42: 在 GR_ZH93 文本表里按关键词找条目 id"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'text')
KW = sys.argv[1] if len(sys.argv) > 1 else '何为幽灵'
for fn in sorted(os.listdir(SRC)):
    if not fn.endswith('.csv'):
        continue
    with io.open(os.path.join(SRC, fn), encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            t = r.get('text_zh') or ''
            if KW in t:
                print('%-28s %-14s res=%-6s idx=%-6s len=%-5s' %
                      (fn.replace('GR_ZH93_text_', ''), r['id'], r['resource'],
                       r['entry_index'], r['len_bytes']))
                print('   text_zh[:60] = %r' % t[:60])
                print('   text_en[:60] = %r' % (r.get('text_en') or '')[:60])
