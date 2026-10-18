# -*- coding: utf-8 -*-
r"""count_legacy_bytes.py — 统计 all_text.csv(hex_zh 列) 里"已被抬成 lead 的旧单字节码"出现次数
闸门抬到 0xB4 ⇒ 危险字节 = 0xB1..0xB3 ; 抬到 0xB5 ⇒ 再加 0xB4
用法: python count_legacy_bytes.py <all_text.csv>
"""
import collections
import csv
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
csv_path = sys.argv[1]
rows = list(csv.DictReader(open(csv_path, encoding='utf-8')))
SK = next(k for k in rows[0].keys() if k.endswith('source'))
print('  行数 %d · 列 %s' % (len(rows), list(rows[0].keys())))
danger = {0xB1: 'B1', 0xB2: 'B2', 0xB3: 'B3', 0xB4: 'B4'}
per_src = collections.defaultdict(lambda: collections.Counter())
tot = collections.Counter()
nbad = 0
for r in rows:
    h = (r.get('hex_zh') or '').strip()
    if not h:
        continue
    try:
        b = bytes.fromhex(h)
    except ValueError:
        continue
    hit = {c: b.count(bytes([c])) for c in danger}
    if any(hit.values()):
        nbad += 1
        src = r.get(SK, '?')
        for c, v in hit.items():
            if v:
                per_src[src][danger[c]] += v
                tot[danger[c]] += v
print('  含危险字节的文本行数 = %d' % nbad)
print('  合计: %s' % dict(tot))
print()
print('  按来源:')
for src in sorted(per_src):
    print('    %-14s %s' % (src, dict(per_src[src])))
print()
print('  ⇒ 这些就是"抬闸门后必须重编码"的落点（每处吞掉后 1 字节 ⇒ 整串错位 ⇒ ASCII 乱码）')
