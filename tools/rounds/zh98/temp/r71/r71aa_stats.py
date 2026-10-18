# -*- coding: utf-8 -*-
r"""r71aa_stats.py — 报告用数字: 字数/字节变化、替换处数、逐条规模"""
import csv
import io
import json
import os
import re
import sys
import hashlib

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LOW = ['SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'] + ['SFXML:T%04d' % i for i in range(50, 63)]
HI = ['SFXML:T0065', 'SFXML:T0066', 'SFXML:T0063', 'SFXML:T0043', 'SFXML:T0044',
      'SFXML:T0046', 'SFXML:T0047', 'SFXML:T0048', 'SFXML:T0064']


def load(p):
    return {r['id']: r for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline=''))}


bak = load(os.path.join(HERE, 'text_backup_before_r71', 'GR_ZH113b_text_long.csv'))
new = load(os.path.join(HERE, 'inject', 'GR_ZH113b_text_long.csv'))
old = load(os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text', 'GR_ZH113_text_long.csv'))


def vis(t):
    return T.WRAP_RE.sub('', t or '').replace('\n', '')


print('=== 规模 ===')
for tag, ids in (('16 条低精准度', LOW), ('9 条高精准度', HI)):
    a = sum(len(vis(bak[i]['text_edited'])) for i in ids)
    b = sum(len(vis(new[i]['text_edited'])) for i in ids)
    print('  %-14s 可见字数 %d -> %d (Δ%+d)  ; 条目 %d' % (tag, a, b, b - a, len(ids)))
a = sum(len(vis(bak[i]['text_edited'])) for i in bak)
b = sum(len(vis(new[i]['text_edited'])) for i in new)
print('  %-14s 可见字数 %d -> %d (Δ%+d)  (58 条长段)' % ('long 表合计', a, b, b - a))
a = sum(len(vis(old[i]['text_edited'])) for i in old)
print('  %-14s 可见字数 %d  (GR_ZH113 缩减版)' % ('对照', a))

print()
print('=== 替换处数 (来自 r71_reduce_map.csv) ===')
mp = list(csv.DictReader(io.open(os.path.join(HERE, 'r71_reduce_map.csv'),
                                encoding='utf-8-sig', newline='')))
print('  合计 %d 处; 消除字样 %d 种 / %d 次'
      % (len(mp), len(set(''.join(r['替换了哪些超范围字'] for r in mp))),
         sum(len(r['替换了哪些超范围字']) for r in mp)))
n_low = sum(1 for r in mp if r['条目id'] in LOW)
print('  其中低精准度 16 条 %d 处 / 高精准度 9 条 %d 处' % (n_low, len(mp) - n_low))

print()
print('=== 逐条: 底本缺字 -> 改了几处 ===')
per = {}
for r in mp:
    per.setdefault(r['条目id'], []).append(r)
from collections import Counter
miss = Counter()
for i in list(bak):
    for ch in vis(bak[i]['text_edited']):
        if ord(ch) >= 0x80 and ch not in (set()):
            pass
import json as J
d = J.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                               'charset_compiled_zh16.json'), encoding='utf-8'))
HAVE = set(d['pair_of']) | set(d['codes']) | set(chr(i) for i in range(0x20, 0x7F))
for i in sorted(bak):
    m = [c for c in vis(bak[i]['text_edited']) if ord(c) >= 0x80 and c not in HAVE]
    n = len(per.get(i, []))
    if m or n:
        print('  %-14s 底本缺 %3d 种 / %3d 次 -> 改 %2d 处 %s'
              % (i, len(set(m)), len(m), n, '(低)' if i in LOW else '(高)'))
