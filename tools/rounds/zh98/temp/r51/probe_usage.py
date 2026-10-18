# -*- coding: utf-8 -*-
"""r51 探针⑦: 28 个单字节码的字在全部文本表里出现几次? 0x92 的记录在哪? 只读。"""
import csv
import io
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib
import dump_font

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
font = dump_font.load_font(ISO)
recs = [x for x in font['faces'] if x[0] == 'default'][0][2]
cs = tcslib.Charset()

print('0x92 的记录 = %s' % (recs[0x92 - 0x20],))
for c in (0x92, 0xAE, 0xFF, 0x9D, 0x9E, 0x9F, 0xA0):
    print('  0x%02X %r rec=%s' % (c, cs.codes.get(c, '?'), recs[c - 0x20]))

TEXTDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'text')
targets = [cs.codes[c] for c in sorted(cs.codes) if 0x80 <= c <= 0x9C and c != 0x92]
print()
print('待查 %d 个字: %s' % (len(targets), ''.join(targets)))
cnt = dict((ch, 0) for ch in targets)
rows_by = dict((ch, 0) for ch in targets)
files = 0
for fn in sorted(os.listdir(TEXTDIR)):
    if not fn.lower().endswith('.csv'):
        continue
    files += 1
    p = os.path.join(TEXTDIR, fn)
    with io.open(p, encoding='utf-8-sig', newline='') as fh:
        rd = csv.DictReader(fh)
        col = None
        for cand in ('text_edited', 'text_zh', 'text'):
            if rd.fieldnames and cand in rd.fieldnames:
                col = cand
                break
        if col is None:
            continue
        for r in rd:
            t = r.get(col) or ''
            hit = [ch for ch in targets if ch in t]
            for ch in hit:
                cnt[ch] += t.count(ch)
                rows_by[ch] += 1
print('扫了 %d 个 CSV' % files)
print()
print('| 字 | 码 | 出现次数 | 所在行数 |')
for ch in sorted(targets, key=lambda c: -cnt[c]):
    code = cs.enc_single[ch]
    print('| %s | 0x%02X | %d | %d |' % (ch, code, cnt[ch], rows_by[ch]))
print()
tot = sum(cnt.values())
print('合计出现 %d 次 (涉及 %d 个不同字)' % (tot, sum(1 for v in cnt.values() if v)))
