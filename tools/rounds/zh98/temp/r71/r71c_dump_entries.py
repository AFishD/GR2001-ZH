# -*- coding: utf-8 -*-
r"""r71c_dump_entries.py — 把目标条目的完整正文 + 缺字明细打到临时文件, 便于人工改写"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix', 'GR_ZH109_text_long.csv')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
have = set(c['pair_of']) | set(c['codes'])

rows = list(csv.DictReader(io.open(SRC, encoding='utf-8-sig', newline='')))
byid = {r['id']: r for r in rows}

TARGET = ['SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'] + ['SFXML:T%04d' % i for i in range(50, 63)]
HI = ['SFXML:T0065', 'SFXML:T0066', 'SFXML:T0063', 'SFXML:T0043', 'SFXML:T0044', 'SFXML:T0046',
      'SFXML:T0047', 'SFXML:T0048', 'SFXML:T0064']

def miss_of(t):
    return [ch for ch in t if ord(ch) >= 0x80 and ch not in have]

with io.open(os.path.join(OUT, 'r71_targets.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for eid in TARGET + HI:
        r = byid[eid]
        t = re.sub(r'(?:\{[Ww][Aa][Rr][Pp]\}){2,}', '\n\n', r['text_edited'] or '')
        m = miss_of(t.replace('{WRAP}', '').replace('{Warp}', '').replace('\n', ''))
        f.write('=' * 100 + '\n')
        f.write('### %s   缺 %d 种 / %d 次 : %s\n' % (eid, len(set(m)), len(m), ''.join(sorted(set(m)))))
        f.write('--- text_en ---\n')
        f.write((r.get('text_en') or '') + '\n')
        f.write('--- text_edited (wrapfix 后, {WRAP} 用 <W> 显示) ---\n')
        f.write(t.replace('{WRAP}', '<W>').replace('{Warp}', '<W>').replace('\n', '\\n\n') + '\n')
        f.write('--- 原始 ({WRAP} 原样) ---\n')
        f.write((r['text_edited'] or '') + '\n\n')
print('->', os.path.join(OUT, 'r71_targets.txt'))
