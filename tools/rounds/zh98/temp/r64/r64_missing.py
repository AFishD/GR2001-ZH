# -*- coding: utf-8 -*-
r"""r64_missing.py — 统计用户新文本里"字库没有的字"

预检报 693 个字有问题。本脚本给出:
  · 有多少**不同**的字 (决定要多少格位)
  · 每个字出现多少次 (决定优先级)
  · 与字库剩余容量 (329 空位) 对比
  · 同时给出"去掉这些字后还能不能表达"的对照 (常见字 vs 生僻字)
只读, 不写任何文件。
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
have = set(c['pair_of']) | set(c['codes'])
print('字库现有字数: %d (对偶 %d + 单字节 %d)' % (len(have), len(c['pair_of']), len(c['codes'])))

miss = Counter()
used = Counter()
for fn in sorted(os.listdir(TXT)):
    if not re.search(r'_text_[^/\\]*\.csv$', fn):
        continue
    rows = list(csv.DictReader(io.open(os.path.join(TXT, fn), encoding='utf-8-sig', newline='')))
    for r in rows:
        t = (r.get('text_edited') or '').strip()
        if not t:
            continue
        t = re.sub(r'\{[Ww][Aa][Rr][Pp]\}', '', t)      # 断点标记不算字
        for ch in t:
            if ch in '\r\n\t ':
                continue
            used[ch] += 1
            if ord(ch) >= 0x80 and ch not in have:
                miss[ch] += 1
print('正文用到的不同字符: %d ; 其中**字库没有的**: %d 种, 共出现 %d 次'
      % (len(used), len(miss), sum(miss.values())))
print()
print('=== 字库没有的字 (按出现次数降序, 前 60) ===')
for i, (ch, n) in enumerate(miss.most_common(60)):
    print('   %-3s U+%04X  %4d 次' % (ch, ord(ch), n), end='\n' if i % 3 == 2 else '')
print()
print()
tot = len(miss)
print('⇒ 需要 **%d 个格位**; 字库剩余空位 **329 个** ⇒ %s'
      % (tot, '放得下' if tot <= 329 else '**放不下, 差 %d 个**' % (tot - 329)))
print()
print('=== 出现次数分布 (决定能不能"先扩高频的") ===')
for lo, hi in ((1, 1), (2, 3), (4, 10), (11, 10 ** 9)):
    k = sum(1 for _ch, n in miss.items() if lo <= n <= hi)
    occ = sum(n for _ch, n in miss.items() if lo <= n <= hi)
    print('   出现 %s 次: %3d 种字, 共 %5d 次' % ('%d' % lo if hi == lo else ('%d-%d' % (lo, hi) if hi < 10 ** 9 else '>=%d' % lo), k, occ))
