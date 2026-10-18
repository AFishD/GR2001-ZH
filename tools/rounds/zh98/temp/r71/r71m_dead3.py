# -*- coding: utf-8 -*-
r"""r71m_dead3.py — step3 诊断(终版): 只按**本轮产物**的文本算引用

LIVE = 本轮改后 3 张注入表 (long=r71_reduced_long, nowrap/short=现役)
     ∪ GR_ZH113 全部 view 表的文本列
★ 不算 GR_ZH113 现役 long 表 —— 它的 58 条**全部会被本轮替换** (text_edited != text_zh),
  所以只被它引用的字在本轮之后就成了死字形 ⇒ 可回收。

输出 r71_dead_chars.csv (含 slot), 并给出"能换几个 / 还差几个"的结论。
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
T113 = os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'text')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

d = json.load(io.open(CS, encoding='utf-8'))
PAIR, CODES = d['pair_of'], d['codes']
HAVE = set(PAIR) | set(CODES) | set(chr(i) for i in range(0x20, 0x7F))
WRAP = re.compile(r'\{[Ww][Aa][Rr][Pp]\}')


def na(s):
    return set(ch for ch in (s or '') if ord(ch) >= 0x80)


live = Counter()
where = defaultdict(set)

NEW = [('本轮long', os.path.join(HERE, 'r71_reduced_long.csv')),
       ('nowrap', os.path.join(T113, 'GR_ZH113_text_long_nowrap.csv')),
       ('short', os.path.join(T113, 'GR_ZH113_text_short.csv'))]
for tag, p in NEW:
    for r in csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')):
        for ch in na(WRAP.sub('', r.get('text_edited') or '')):
            live[ch] += 1
            where[ch].add(tag)

for fn in sorted(os.listdir(T113)):
    if not fn.startswith('GR_ZH113_view_') or not fn.endswith('.csv'):
        continue
    tag = fn.replace('GR_ZH113_view_', 'view:').replace('.csv', '')
    for r in csv.DictReader(io.open(os.path.join(T113, fn), encoding='utf-8-sig', newline='')):
        for col in ('text', 'text_preview'):
            if col in r:
                for ch in na(r[col]):
                    live[ch] += 1
                    where[ch].add(tag)

# 旧 long 表 (仅供参考: 这些字"只靠旧文本活着")
old = Counter()
for r in csv.DictReader(io.open(os.path.join(T113, 'GR_ZH113_text_long.csv'),
                               encoding='utf-8-sig', newline='')):
    for ch in na(WRAP.sub('', r.get('text_edited') or '')):
        old[ch] += 1

dead_pair = sorted(c for c in PAIR if c not in live)
dead_single = sorted(c for c in CODES if c not in live)
print('LIVE 非 ASCII: %d 种 / %d 次' % (len(live), sum(live.values())))
print('可回收对偶槽: %d 种' % len(dead_pair))
for i in range(0, len(dead_pair), 60):
    print('   ' + ' '.join(dead_pair[i:i + 60]))
print('可回收单字节码: %d 种' % len(dead_single))
print('   ' + ' '.join(dead_single))
print()
print('其中"只靠旧缩减版 long 表活着"的: %d 种'
      % sum(1 for c in dead_pair + dead_single if c in old))
print('   ' + ' '.join(c for c in dead_pair + dead_single if c in old))

need = Counter()
ne = defaultdict(set)
for r in csv.DictReader(io.open(os.path.join(HERE, 'r71_reduced_long.csv'),
                               encoding='utf-8-sig', newline='')):
    t = WRAP.sub('', r.get('text_edited') or '')
    for ch in t:
        if ord(ch) >= 0x80 and ch not in HAVE:
            need[ch] += 1
            ne[ch].add(r['id'])
print()
print('高精准度仍缺 %d 种 / %d 次 ; 可回收 %d 个 ⇒ %s'
      % (len(need), sum(need.values()), len(dead_pair) + len(dead_single),
         '够' if len(dead_pair) + len(dead_single) >= len(need) else
         '不够, 还差 %d 个' % (len(need) - len(dead_pair) - len(dead_single))))

with io.open(os.path.join(HERE, 'r71_dead_chars.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', '种类', 'slot(对偶)', 'pair_code_b1b2', 'single_byte',
                '本轮后引用次数', '死因'])
    for ch in sorted(dead_pair, key=lambda c: (PAIR[c][0] - 0xA1) * 94 + (PAIR[c][1] - 0xA1)):
        b1, b2 = PAIR[ch]
        w.writerow([ch, 'U+%04X' % ord(ch), 'pair', (b1 - 0xA1) * 94 + (b2 - 0xA1),
                    '%02X %02X' % (b1, b2), '', 0,
                    '本轮产物文本 0 引用' + ('; 旧缩减版 long 表曾用 %d 次' % old[ch] if ch in old else '')])
    for ch in dead_single:
        w.writerow([ch, 'U+%04X' % ord(ch), 'single', '', '', '%02X' % CODES[ch], 0,
                    '本轮产物文本 0 引用' + ('; 旧缩减版 long 表曾用 %d 次' % old[ch] if ch in old else '')])
print('-> r71_dead_chars.csv')
