# -*- coding: utf-8 -*-
r"""p13_find.py — 5 个"画不出来"的字出现在哪几条译文里 (给实机取证用)。"""
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
tdir = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'text')
CHARS = '若终脆膛著纤荐'
for fn in sorted(os.listdir(tdir)):
    if not fn.endswith('.csv') or '_view_' in fn:
        continue
    with open(os.path.join(tdir, fn), encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            t = r.get('text_edited') or ''
            hit = [c for c in CHARS if c in t]
            if hit:
                print('%s\n   id=%s kind=%s container=%s resource=%s' %
                      (' '.join(hit), r.get('id'), r.get('kind'), r.get('container'),
                       r.get('resource')))
                print('   %s' % t.replace('\n', ' / ')[:220])
