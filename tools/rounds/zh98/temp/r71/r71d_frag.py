# -*- coding: utf-8 -*-
r"""r71d_frag.py — 为 16 条低精准度条目列出「含缺字的片段」工作清单

口径:
  · 可用字集 = charset_compiled_zh16.json 的 pair_of + codes  (1504)
  · 把正文按「非汉字段」切开: 只保留 [\u4e00-\u9fff] 连成的 run, 并带上前后各 1 个字符的上下文
  · 每个 run 里若含缺字, 输出一条:  entry_id | run | missing | 出现次数
输出: work/builds/GR_ZH98/temp/r71/r71_frag.csv  + r71_frag.txt(人读)
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix',
                   'GR_ZH109_text_long.csv')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
HAVE = set(c['pair_of']) | set(c['codes'])
PUNCT = set()

LOW = ['SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'] + ['SFXML:T%04d' % i for i in range(50, 63)]

rows = {r['id']: r for r in csv.DictReader(io.open(SRC, encoding='utf-8-sig', newline=''))}


def wrapfix(t):
    return re.sub(r'(?:\{[Ww][Aa][Rr][Pp]\}){2,}', '\n\n', t or '')


def is_cjk(ch):
    return '\u4e00' <= ch <= '\u9fff'


def bad(ch):
    return ord(ch) >= 0x80 and ch not in HAVE


frag_rows = []
seen_global = defaultdict(set)
for eid in LOW:
    t = wrapfix(rows[eid]['text_edited'])
    # 切成 CJK run (记录起始下标)
    runs = []
    i = 0
    n = len(t)
    while i < n:
        if is_cjk(t[i]):
            j = i
            while j < n and is_cjk(t[j]):
                j += 1
            runs.append((i, j, t[i:j]))
            i = j
        else:
            i += 1
    for (i, j, run) in runs:
        miss = sorted(set(ch for ch in run if bad(ch)))
        if not miss:
            continue
        ctx = t[max(0, i - 2):i] + '[' + run + ']' + t[j:j + 2]
        frag_rows.append(dict(id=eid, pos=i, run=run, missing=''.join(miss),
                              ctx=ctx.replace('\n', '\\n')))
        for ch in miss:
            seen_global[ch].add(eid)

with io.open(os.path.join(HERE, 'r71_frag.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['id', 'pos', 'run', 'missing', 'ctx'])
    for r in frag_rows:
        w.writerow([r['id'], r['pos'], r['run'], r['missing'], r['ctx']])

with io.open(os.path.join(HERE, 'r71_frag.txt'), 'w', encoding='utf-8', newline='\n') as f:
    cur = None
    for r in frag_rows:
        if r['id'] != cur:
            cur = r['id']
            f.write('\n' + '#' * 90 + '\n### %s\n' % cur)
        f.write('  %-28s -> %s\n' % (r['run'], r['missing']))

# 统计
miss_all = Counter()
for r in frag_rows:
    for ch in r['run']:
        if bad(ch):
            miss_all[ch] += 1
print('低精准度 16 条: 片段 %d 个; 缺字 %d 种 / %d 次'
      % (len(frag_rows), len(miss_all), sum(miss_all.values())))
byid = Counter(r['id'] for r in frag_rows)
print('每条片段数:', dict(byid))

# 全库缺字 (三张表? 这里只 long 表; 另两张表未改过)
allmiss = Counter()
for r in rows.values():
    t = wrapfix(r['text_edited'])
    for ch in t:
        if bad(ch):
            allmiss[ch] += 1
print('恢复底本后(long 表 58 条) 缺字: %d 种 / %d 次' % (len(allmiss), sum(allmiss.values())))
hi = {ch: n for ch, n in allmiss.items()
      if not any(ch in r['run'] for r in frag_rows)}
print('高精准度(16 条之外) 缺字: %d 种 / %d 次' % (len(hi), sum(hi.values())))
with io.open(os.path.join(HERE, 'r71_hi_chars.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for ch, n in sorted(hi.items(), key=lambda x: -x[1]):
        f.write('%s\t%d\n' % (ch, n))
print('-> r71_frag.csv / r71_frag.txt / r71_hi_chars.txt')
