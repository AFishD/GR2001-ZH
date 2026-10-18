# -*- coding: utf-8 -*-
"""r39: 检查 view 表里的中文行 —— 区分「真文本」与「噪声巧合」。只读。"""
import collections
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
TEXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CJK = re.compile(r'[\u4e00-\u9fff]')
CJK2 = re.compile(r'[\u4e00-\u9fff]{2,}')


def rows_of(p):
    with io.open(p, 'r', encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


for fn in sorted(os.listdir(TEXT)):
    if '_view_' not in fn or not fn.endswith('.csv'):
        continue
    rows = rows_of(os.path.join(TEXT, fn))
    if not rows:
        print('%-46s 0 行' % fn)
        continue
    n_cjk = sum(1 for r in rows if r.get('has_cjk') == 'yes')
    cjk_rows = [r for r in rows if r.get('has_cjk') == 'yes']
    n_cjk2 = sum(1 for r in cjk_rows if CJK2.search(r['text']))
    kinds = collections.Counter(r['text_kind'] for r in rows)
    print('\n== %-42s %6d 行; exact=%d message=%d; 含中文 %d (其中连续汉字 %d)'
          % (fn, len(rows), kinds['exact'], kinds['message'], n_cjk, n_cjk2))
    # 随机/前几条 sample
    for r in rows[:3]:
        print('   样本  %-30s %r' % (r['container'][:30], r['text'][:100]))
    if cjk_rows:
        with2 = [r for r in cjk_rows if CJK2.search(r['text'])]
        for r in with2[:12]:
            print('   ★连续汉字 %-28s %r' % (r['container'][:28], r['text'][:100]))
        one = [r for r in cjk_rows if not CJK2.search(r['text'])]
        for r in one[:6]:
            print('   单汉字   %-28s %r' % (r['container'][:28], r['text'][:100]))
