# -*- coding: utf-8 -*-
r"""m27_zhiluo.py — 检查 志/略/× 以及的/你 的现状 (决定 gate 抬到 0xB1 是否可行)。
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
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
txt = []
for fn in sorted(os.listdir(TXT)):
    if fn.endswith('.csv'):
        with open(os.path.join(TXT, fn), encoding='utf-8-sig', newline='') as fh:
            txt += [(r.get('id'), r.get('text_edited') or '') for r in csv.DictReader(fh)]
allt = '\n'.join(t for _i, t in txt)

for ch in '志略×的你荐':
    n = allt.count(ch)
    c = codes.get(ch)
    p = pair_of.get(ch)
    print('%s : 出现 %d 次 ; 单字节码=%s ; 对偶码=%s'
          % (ch, n, ('0x%02X' % c) if c is not None else '无',
             ('%02X%02X(lead=0x%02X)' % (p[0], p[1], p[0])) if p else '无'))

print()
print('== 用户译文里含 志/略/× 的条目 ==')
for i, t in txt:
    for ch in '志略×':
        if ch in t:
            k = t.index(ch)
            print('  %-14s %s ... %s' % (i, ch, t[max(0, k - 14):k + 14].replace('\n', '\\n')))
            break

print()
print('== BTN 手柄图标标记使用次数 (0xB1/0xB5/0xE7/0xF1 必须保留) ==')
import re
for c in (0xE0B1, 0xE0B5, 0xE0E7, 0xE0F1):
    pat = re.compile(r'\{\{\s*BTN\s*:\s*%04X\s*\}\}' % c, re.I)
    print('  {{BTN:%04X}} : %d 次' % (c, len(pat.findall(allt))))
print()
print('== 0xAE..0xB0 这几个单字节码当前的字 ==')
inv = {}
for ch, c in codes.items():
    inv.setdefault(c, []).append(ch)
for c in range(0xAE, 0xB4):
    print('  0x%02X : %s' % (c, ''.join(inv.get(c, [])) or '(空)'))
