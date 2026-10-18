# -*- coding: utf-8 -*-
r"""r71ac_quotes.py — 引号体检: 找出"双引号嵌套"(同一层里再开双引号) 与不配对处

背景: 字库里没有 ‘’(U+2018/2019), 底本里用单引号的强调(如 T0056 的 ‘乐在其中’)
      只能改成双引号 ⇒ 会和外层对话引号打架。
"""
import csv
import io
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
NEW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, 'work/builds/GR_ZH113_B/text/GR_ZH113_B_text_long.csv')
OLD = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, 'work/builds/GR_ZH113/text/GR_ZH113_text_long.csv')
for tag, p in (('本轮产物', NEW), ('GR_ZH113 ', OLD)):
    rows = list(csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')))
    print('== %s ==' % tag)
    bad = 0
    for r in rows:
        t = r['text_edited'] or ''
        d = 0
        for i, ch in enumerate(t):
            if ch == '“':
                d += 1
                if d >= 2:
                    bad += 1
                    print('   [嵌套] %-14s …%s…' % (r['id'], t[max(0, i - 20):i + 20].replace('\n', '⏎')))
            elif ch == '”':
                d -= 1
        if d != 0:
            bad += 1
            print('   [不配对 depth=%d] %s' % (d, r['id']))
    print('   问题 %d 处' % bad)
