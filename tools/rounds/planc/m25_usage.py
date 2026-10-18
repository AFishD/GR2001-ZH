# -*- coding: utf-8 -*-
r"""m25_usage.py — 用户当前译文里每个单字节码/缺字的使用次数 (决定能否回收闲置的单字节码)。
"""
import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
TXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
js = json.load(open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                 'charset_compiled_zh16.json'), encoding='utf-8'))
codes = {ch: int(v) for ch, v in js['codes'].items()}
MISSING = '虽螺衍衣裂誉贡轮迟造钢题额鼓（）'
MOVE = '荐'

blob = []
for fn in sorted(os.listdir(TXT)):
    if fn.endswith('.csv'):
        with open(os.path.join(TXT, fn), encoding='utf-8-sig', newline='') as fh:
            for row in csv.DictReader(fh):
                blob.append(row.get('text_edited') or '')
allt = '\n'.join(blob)
print('用户译文字符总数 %d (含换行)' % len(allt))

print()
print('== 111 个单字节码字的使用次数 (升序) ==')
zero = []
for ch, c in sorted(codes.items(), key=lambda kv: allt.count(kv[0])):
    n = allt.count(ch)
    if n == 0:
        zero.append((ch, c))
    print('  0x%02X %s %6d' % (c, ch, n), end='')
    if (sorted(codes, key=lambda k: codes[k]).index(ch) + 1) % 6 == 0:
        print()
print()
print('  **零次使用** 的单字节码: %s'
      % ' '.join('%s(0x%02X)' % (ch, c) for ch, c in zero) or '无')

print()
print('== 16 个缺字 + 荐 的使用次数 ==')
for ch in MISSING + MOVE:
    print('  %s : %d 次' % (ch, allt.count(ch)), end='')
print()
