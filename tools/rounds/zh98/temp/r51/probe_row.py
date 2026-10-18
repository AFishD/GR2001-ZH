# -*- coding: utf-8 -*-
"""r51 探针⑧c: 那 29 次命中落在哪一行? 只读。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

cs = tcslib.Charset()
TD = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text')
files = ['GR_ZH98_text_long.csv', 'GR_ZH98_text_long_nowrap.csv', 'GR_ZH98_text_short.csv']
targets = set(cs.codes[c] for c in sorted(cs.codes) if 0x80 <= c <= 0x9C)
for fn in files:
    with io.open(os.path.join(TD, fn), encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            t = r.get('text_zh') or ''
            hit = targets & set(t)
            if hit:
                print('=== %s | id=%s resource=%s container=%s idx=%s off=%s kind=%s'
                      % (fn, r.get('id'), r.get('resource'), r.get('container'),
                         r.get('entry_index'), r.get('offset'), r.get('kind')))
                print('    命中字 (%d): %s' % (len(hit), ''.join(sorted(hit))))
                print('    text_zh     : %r' % t[:400])
                print('    text_edited : %r' % (r.get('text_edited') or '')[:400])
                print('    text_en     : %r' % (r.get('text_en') or '')[:200])
                print('    note        : %r' % (r.get('note') or '')[:200])
                print()
