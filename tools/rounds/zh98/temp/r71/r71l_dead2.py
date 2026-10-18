# -*- coding: utf-8 -*-
r"""r71l_dead2.py — step3 诊断(修正版): 非 ASCII 全字符口径, 找出可回收字形

口径:
  LIVE = 本轮改后 3 张注入表的正文 ∪ GR_ZH113 全部 view 表的文本列 (取所有 >=0x80 的字符)
  DEAD_pair  = pair_of 的字 − LIVE
  DEAD_single= codes  的字 − LIVE
另外统计: 每个 DEAD 字**最后一次**出现在哪 (旧 long 表 / view 表), 以说明它为什么死了。
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


def nonascii(s):
    return set(ch for ch in (s or '') if ord(ch) >= 0x80)


live = Counter()
where = defaultdict(set)

files = [('long(本轮r71)', os.path.join(HERE, 'r71_reduced_long.csv')),
         ('long(GR_ZH113缩减/将被替换)', os.path.join(T113, 'GR_ZH113_text_long.csv')),
         ('long_nowrap', os.path.join(T113, 'GR_ZH113_text_long_nowrap.csv')),
         ('short', os.path.join(T113, 'GR_ZH113_text_short.csv'))]
for tag, p in files:
    rows = list(csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')))
    for r in rows:
        for ch in nonascii(WRAP.sub('', r.get('text_edited') or '')):
            live[ch] += 1
            where[ch].add(tag)

for fn in sorted(os.listdir(T113)):
    if not fn.startswith('GR_ZH113_view_') or not fn.endswith('.csv'):
        continue
    tag = fn.replace('GR_ZH113_view_', 'view:').replace('.csv', '')
    for r in csv.DictReader(io.open(os.path.join(T113, fn), encoding='utf-8-sig', newline='')):
        for col in ('text', 'text_preview'):
            if col in r:
                for ch in nonascii(r[col]):
                    live[ch] += 1
                    where[ch].add(tag)

print('LIVE 非 ASCII 字符: %d 种 / %d 次' % (len(live), sum(live.values())))

dead_pair = sorted(c for c in PAIR if c not in live)
dead_single = sorted(c for c in CODES if c not in live)
print()
print('对偶槽可回收: %d 种' % len(dead_pair))
print('   ' + ' '.join(dead_pair))
print('单字节码可回收: %d 种' % len(dead_single))
print('   ' + ' '.join(dead_single))

# 说明每个死字最后出现在哪
print()
print('=== 死字溯源 (它出现在哪些"将被替换/只读"的地方) ===')
for ch in dead_pair + dead_single:
    ws = where.get(ch, set())
    print('  %s U+%04X : %s' % (ch, ord(ch), ', '.join(sorted(ws)) if ws else '(任何地方都没有)'))

out = os.path.join(HERE, 'r71_dead_chars.csv')
with io.open(out, 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', '种类', 'slot(对偶)', 'pair_code_b1b2', 'single_byte',
                '本轮后出现次数', '死因'])
    for ch in sorted(dead_pair, key=lambda c: (PAIR[c][0] - 0xA1) * 94 + (PAIR[c][1] - 0xA1)):
        b1, b2 = PAIR[ch]
        w.writerow([ch, 'U+%04X' % ord(ch), 'pair', (b1 - 0xA1) * 94 + (b2 - 0xA1),
                    '%02X %02X' % (b1, b2), '', 0,
                    '本轮后无任何文本引用' + ('; 旧缩减版曾用' if ch in where else '')])
    for ch in dead_single:
        w.writerow([ch, 'U+%04X' % ord(ch), 'single', '', '', '%02X' % CODES[ch], 0,
                    '本轮后无任何文本引用' + ('; 旧缩减版曾用' if ch in where else '')])
print('\n-> %s' % out)
