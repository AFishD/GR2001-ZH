# -*- coding: utf-8 -*-
r"""r71k_dead.py — step3 诊断: 1504 个对偶槽位里, 哪些字**任何文本都不再用** (可回收)

口径 (与 round49 `_font_recycle_zh98` 同源, 但按本轮文本状态重算):
  LIVE = GR_ZH113b 三张可注入表(本轮改后的 long + 现役 nowrap/short)的正文
       ∪ GR_ZH113 的 9 张 view 表里所有含汉字的文本列
       (view 表 = 盘上 xml/txt/mis/atr/其它 RES/ELF/ISO 文件/二进制容器可读串的扫描结果)
  DEAD = charset pair_of 的 1504 个字 − LIVE

输出:
  work/builds/GR_ZH98/temp/r71/r71_dead_chars.csv    可回收字 (含 slot / 码位 / 证据)
  work/builds/GR_ZH98/temp/r71/r71_hi_need.csv       高精准度条目还缺的 47 字的依据
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
PAIR = d['pair_of']                       # char -> [b1, b2]
CODES = d['codes']                        # char -> byte
PAIRSET = set(PAIR)
HAVE = PAIRSET | set(CODES) | set(chr(i) for i in range(0x20, 0x7F))
WRAP = re.compile(r'\{[Ww][Aa][Rr][Pp]\}')


def cjk(s):
    return set(ch for ch in (s or '') if '\u4e00' <= ch <= '\u9fff')


live = Counter()          # char -> 出现次数 (只在汉字里数)
src_of = defaultdict(set)

# ---- 1) 三张可注入表 ----
TABLES = ['r71_reduced_long.csv', None, None]      # 本轮改后的 long
files = [('long(本轮)', os.path.join(HERE, 'r71_reduced_long.csv')),
         ('long_nowrap', os.path.join(T113, 'GR_ZH113_text_long_nowrap.csv')),
         ('short', os.path.join(T113, 'GR_ZH113_text_short.csv'))]
for tag, p in files:
    rows = list(csv.DictReader(io.open(p, encoding='utf-8-sig', newline='')))
    for r in rows:
        t = r.get('text_edited') or ''
        for ch in cjk(WRAP.sub('', t)):
            live[ch] += 1
            src_of[ch].add(tag)
    print('  %-14s %5d 行' % (tag, len(rows)))

# ---- 2) view 表 ----
for fn in sorted(os.listdir(T113)):
    if not fn.startswith('GR_ZH113_view_') or not fn.endswith('.csv'):
        continue
    rows = list(csv.DictReader(io.open(os.path.join(T113, fn), encoding='utf-8-sig', newline='')))
    n = 0
    for r in rows:
        for col in ('text', 'text_preview'):
            if col not in r:
                continue
            for ch in cjk(r[col]):
                live[ch] += 1
                src_of[ch].add(fn.replace('GR_ZH113_view_', '').replace('.csv', ''))
                n += 1
    print('  %-42s %6d 行, 汉字 %d 次' % (fn, len(rows), n))

print()
print('LIVE 汉字: %d 种 / %d 次' % (len(live), sum(live.values())))

dead = sorted(set(c for c in PAIRSET if c not in live))
print('DEAD (1504 对偶槽里任何文本都没用到): %d 种' % len(dead))
print('  ' + ''.join(dead))

# ---- 3) 高精准度条目还缺的 47 字 + 依据 ----
hi_rows = list(csv.DictReader(io.open(os.path.join(HERE, 'r71_entries.csv'),
                                      encoding='utf-8-sig', newline='')))
need = Counter()
need_entries = defaultdict(set)
for r in hi_rows:
    if r['scene'] != '特别收录其它':
        continue
    for ch in r['missing']:
        need[ch] += int(r['n_occ']) if len(r['missing']) == 1 else 1
        need_entries[ch].add(r['id'])

# 更准的口径: 直接在改后的表里数
base = {r['id']: r for r in csv.DictReader(
    io.open(os.path.join(HERE, 'r71_reduced_long.csv'), encoding='utf-8-sig', newline=''))}
need2 = Counter()
need2_entries = defaultdict(set)
for eid, r in base.items():
    t = WRAP.sub('', (r.get('text_edited') or ''))
    for ch in t:
        if ord(ch) >= 0x80 and ch not in HAVE:
            need2[ch] += 1
            need2_entries[ch].add(eid)

print()
print('高精准度条目仍缺: %d 种 / %d 次' % (len(need2), sum(need2.values())))
for ch, n in sorted(need2.items(), key=lambda x: (-x[1], x[0])):
    print('   %s U+%04X  %d 次  %s' % (ch, ord(ch), n, ' '.join(sorted(need2_entries[ch]))))

with io.open(os.path.join(HERE, 'r71_dead_chars.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', 'slot', 'pair_code_b1b2', '出现次数(全部文本)', '说明'])
    for ch in sorted(dead, key=lambda c: PAIR[c][0] * 94 + PAIR[c][1]):
        b1, b2 = PAIR[ch]
        slot = (b1 - 0xA1) * 94 + (b2 - 0xA1)
        w.writerow([ch, 'U+%04X' % ord(ch), slot, '%02X %02X' % (b1, b2), 0,
                    '任何文本(3 张注入表 + 9 张 view 表)里 0 次'])
print('\n-> r71_dead_chars.csv')

with io.open(os.path.join(HERE, 'r71_hi_need.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', '需要次数', '出现在哪些条目', '条目数'])
    for ch, n in sorted(need2.items(), key=lambda x: (-x[1], x[0])):
        w.writerow([ch, 'U+%04X' % ord(ch), n, ' '.join(sorted(need2_entries[ch])),
                    len(need2_entries[ch])])
print('-> r71_hi_need.csv')

# ---- 4) 覆盖率 ----
print()
print('可回收 %d 个 vs 高精准度还缺 %d 个 ⇒ %s'
      % (len(dead), len(need2),
         '够换' if len(dead) >= len(need2) else '不够, 差 %d 个' % (len(need2) - len(dead))))
