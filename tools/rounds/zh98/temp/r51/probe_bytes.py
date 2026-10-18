# -*- coding: utf-8 -*-
"""r51 探针⑧: 盘上**实际字节**里, 28 个单字节码 (0x80..0x9C) 用了多少次? (只看 3 张可注入表) 只读。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib

cs = tcslib.Charset()
TD = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text')
files = ['GR_ZH98_text_long.csv', 'GR_ZH98_text_long_nowrap.csv', 'GR_ZH98_text_short.csv']
cnt = dict((c, 0) for c in cs.codes if 0x80 <= c <= 0x9C)
rows = dict((c, set()) for c in cnt)
tot_rows = 0
for fn in files:
    p = os.path.join(TD, fn)
    with io.open(p, encoding='utf-8-sig', newline='') as fh:
        rd = csv.DictReader(fh)
        for r in rd:
            tot_rows += 1
            key = r.get('key') or r.get('id') or ''
            raw = r.get('bytes_hex') or ''
            for c in list(cnt):
                if ('%02X' % c) in raw:
                    cnt[c] += 1
                    rows[c].add((fn, key))
print('3 张可注入表共 %d 行' % tot_rows)
print()
print('| 码 | 字 | 出现在多少行 |')
for c in sorted(cnt, key=lambda x: -cnt[x]):
    if cnt[c]:
        print('| 0x%02X | %s | %d |' % (c, cs.codes[c], cnt[c]))
print()
print('=> 28 个码里有 %d 个在盘上文本里真的被用到' % sum(1 for c in cnt if cnt[c]))

# 看看有没有 bytes_hex 列
with io.open(os.path.join(TD, files[0]), encoding='utf-8-sig', newline='') as fh:
    print('列名: %s' % fh.readline().strip())
