# -*- coding: utf-8 -*-
r"""_find_text.py — 在只读文本表里找「何为幽灵？」长文与含 中/斗/抖 的条目。

只读, 不改任何文件。用来回答: 实机那一页到不到「斗」/「抖」?
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

TXT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   '..', '..', '..', 'text'))
FILES = ['GR_ZH94_text_long.csv', 'GR_ZH94_text_long_nowrap.csv',
         'GR_ZH94_text_short.csv', 'GR_ZH94_text.txt']
NEEDLES = ['何为幽灵', '幽灵行动中', '中士', '斗', '抖']

for fn in FILES:
    p = os.path.join(TXT, fn)
    if not os.path.isfile(p):
        print('!! 缺 %s' % p)
        continue
    print('=' * 78)
    print('### %s' % fn)
    with open(p, encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            for nd in NEEDLES:
                if nd in line:
                    s = line.rstrip('\n')
                    print('[%s] %s:%d  %s' % (nd, fn, i, s[:300]))
                    break
