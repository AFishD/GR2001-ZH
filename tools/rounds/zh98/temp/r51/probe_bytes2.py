# -*- coding: utf-8 -*-
"""r51 探针⑧b: 用 text_zh (盘上字节解码出来的文本) 统计 28 个单字节码的**真实用量**。只读。"""
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
targets = [cs.codes[c] for c in sorted(cs.codes) if 0x80 <= c <= 0x9C]
cnt = dict((ch, 0) for ch in targets)
nrows = 0
for fn in files:
    with io.open(os.path.join(TD, fn), encoding='utf-8-sig', newline='') as fh:
        for r in csv.DictReader(fh):
            nrows += 1
            t = r.get('text_zh') or ''
            e = r.get('text_edited') or ''
            for ch in targets:
                if ch in t:
                    cnt[ch] += t.count(ch)
                if ch in e:
                    cnt.setdefault('ED_' + ch, 0)
                    cnt['ED_' + ch] += e.count(ch)
print('3 张表 %d 行' % nrows)
print('| 字 | 码 | text_zh 里出现 | text_edited 里出现 |')
tot = 0
for ch in sorted(targets, key=lambda c: -cnt[c]):
    ed = cnt.get('ED_' + ch, 0)
    tot += cnt[ch]
    if cnt[ch] or ed:
        print('| %s | 0x%02X | %d | %d |' % (ch, cs.enc_single[ch], cnt[ch], ed))
print()
print('text_zh 里 28 个字合计 %d 次; 非零的字 %d 个'
      % (tot, sum(1 for ch in targets if cnt[ch])))
