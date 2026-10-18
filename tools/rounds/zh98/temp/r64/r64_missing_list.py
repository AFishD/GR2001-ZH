# -*- coding: utf-8 -*-
r"""r64_missing_list.py — 导出"新版译文里字库没有的字"清单 (供人工改文案)

产出两张表 (放 r64/):
  · missing_chars.csv   每个缺字: 字符/码位/出现次数/在哪些条目里出现
  · missing_entries.csv 每个含缺字的条目: id/表/缺字数/缺哪些字/现文案片段
只读源文本, 不写盘。
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
OUT = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
have = set(c['pair_of']) | set(c['codes'])

cnt = Counter()
where = defaultdict(list)
entries = []
for fn in sorted(os.listdir(TXT)):
    if not re.search(r'_text_[^/\\]*\.csv$', fn):
        continue
    rows = list(csv.DictReader(io.open(os.path.join(TXT, fn), encoding='utf-8-sig', newline='')))
    for r in rows:
        t = (r.get('text_edited') or '').strip()
        if not t:
            continue
        t2 = re.sub(r'\{[Ww][Aa][Rr][Pp]\}', '', t)
        miss = sorted({ch for ch in t2 if ord(ch) >= 0x80 and ch not in have})
        if not miss:
            continue
        for ch in miss:
            n = t2.count(ch)
            cnt[ch] += n
            where[ch].append('%s:%s' % (fn.split('_text_')[0], r['id']))
        entries.append((fn, r['id'], len(miss), ''.join(miss), t2[:60].replace('\n', ' ')))

with io.open(os.path.join(OUT, 'missing_chars.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', 'count', 'in_entries', 'sample_entries'])
    for ch, n in cnt.most_common():
        w.writerow([ch, 'U+%04X' % ord(ch), n, len(where[ch]), ' '.join(where[ch][:4])])

with io.open(os.path.join(OUT, 'missing_entries.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['table', 'id', 'n_missing', 'missing_chars', 'text_head'])
    for fn, i, n, ms, head in sorted(entries, key=lambda x: -x[2]):
        w.writerow([fn, i, n, ms, head])

print('缺字 %d 种, 共 %d 次; 涉及条目 %d 条' % (len(cnt), sum(cnt.values()), len(entries)))
print('→ missing_chars.csv (%d 行), missing_entries.csv (%d 行)' % (len(cnt), len(entries)))
print()
print('缺字最多的 30 个:')
line = []
for i, (ch, n) in enumerate(cnt.most_common(30)):
    line.append('%s%d' % (ch, n))
    if i % 10 == 9:
        print('   ' + ' '.join(line)); line = []
if line:
    print('   ' + ' '.join(line))
