# -*- coding: utf-8 -*-
r"""cmp_text_csv.py — 逐行比对两份 all_text.csv 的 hex_zh，判断文本是否被改过
用法: python cmp_text_csv.py <csvA> <csvB>
"""
import csv
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
A, B = sys.argv[1], sys.argv[2]


def load(p):
    rows = list(csv.DictReader(open(p, encoding='utf-8')))
    sk = next(k for k in rows[0].keys() if k.endswith('source'))
    d = {}
    for r in rows:
        d[(r[sk], r.get('key', ''))] = (r.get('hex_zh') or '').strip()
    return d


a, b = load(A), load(B)
print('  A=%d 行  B=%d 行  key 交集=%d' % (len(a), len(b), len(set(a) & set(b))))
diff = [k for k in set(a) & set(b) if a[k] != b[k]]
print('  hex_zh 不同的行 = %d' % len(diff))
by = {}
for k in diff:
    by[k[0]] = by.get(k[0], 0) + 1
print('  按来源: %s' % by)
print()
for k in diff[:6]:
    print('  [%s] %s' % (k[0], k[1][:60]))
    print('      A(%d B): %s' % (len(a[k]) // 2, a[k][:96]))
    print('      B(%d B): %s' % (len(b[k]) // 2, b[k][:96]))
print()
print('  ⇒ 若"不同 = 0" ⇒ 文本一个字都没被改过 ⇒ 抬闸门后所有旧单字节码都会吞字节（乱码根源）')
