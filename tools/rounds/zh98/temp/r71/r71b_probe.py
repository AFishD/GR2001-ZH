# -*- coding: utf-8 -*-
r"""r71b_probe.py — 摸清三张可注入表的列结构 / text_edited 与 text_zh 的差异面"""
import csv
import io
import json
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CAND = [
    ('109bak', r'work\builds\GR_ZH109\text_backup_before_wrapfix'),
    ('109on',  r'work\builds\GR_ZH109\text'),
    ('113on',  r'work\builds\GR_ZH113\text'),
    ('111on',  r'work\builds\GR_ZH111\text'),
]
for tag, rel in CAND:
    d = os.path.join(REPO, rel)
    print('===', tag, rel)
    for fn in sorted(os.listdir(d)):
        if not re.search(r'_text_[^/\\]*\.csv$', fn):
            continue
        rows = list(csv.DictReader(io.open(os.path.join(d, fn), encoding='utf-8-sig', newline='')))
        cols = list(rows[0].keys()) if rows else []
        has_ed = 'text_edited' in cols
        n_ed = sum(1 for r in rows if (r.get('text_edited') or '').strip())
        diff = 0
        if has_ed:
            for r in rows:
                a = (r.get('text_zh') or '')
                b = (r.get('text_edited') or '')
                if b.strip() and a != b:
                    diff += 1
        nl = sum(1 for r in rows if (r.get('text_edited') or '').strip() and '\n' in r['text_edited'])
        pair = sum(1 for r in rows if (r.get('text_edited') or '') and re.search(r'(?:\{[Ww][Aa][Rr][Pp]\}){2,}', r['text_edited']))
        print('  %-38s rows=%-5d cols=%s' % (fn, len(rows), ','.join(cols)))
        print('      text_edited 非空=%d  与 text_zh 不同=%d  含换行=%d  含紧邻{WRAP}=%d' % (n_ed, diff, nl, pair))
