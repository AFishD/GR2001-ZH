# -*- coding: utf-8 -*-
r"""fix_times.py — 把 long 表 text_edited 里的 × (U+00D7) 换成小写 x (用户要求)
   只动 text_edited 列; text_zh / text_en / note 一律不动。"""
import csv
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text', 'GR_ZH92_text_long.csv')
TIMES, LOWX = '\u00d7', 'x'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    with io.open(P, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    cols = list(rows[0].keys())
    n = 0
    for r in rows:
        c = r['text_edited'].count(TIMES)
        if c:
            r['text_edited'] = r['text_edited'].replace(TIMES, LOWX)
            n += c
    print('替换 %d 处 × → x, 涉及 %d 条' % (n, sum(1 for r in rows if LOWX in r['text_edited'])))
    with io.open(P, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n', quoting=csv.QUOTE_MINIMAL)
        w.writeheader()
        w.writerows(rows)
    # 复核
    with io.open(P, encoding='utf-8-sig', newline='') as f:
        rows2 = list(csv.DictReader(f))
    left = sum(r['text_edited'].count(TIMES) for r in rows2)
    note_left = sum(r['note'].count(TIMES) for r in rows2)
    print('复核: 行数 %d (原 %d) | text_edited 里 × 剩 %d | note 里 × 仍有 %d (不动)' %
          (len(rows2), len(rows), left, note_left))
    for r in rows2:
        if 'x' in r['text_edited'] and any(k in r['text_edited'] for k in ('51毫米', '54毫米', '45毫米', '19毫米', '39毫米')):
            i = r['text_edited'].find('x')
            print('   %s: …%s…' % (r['id'], r['text_edited'][max(0, i - 20):i + 16]))


if __name__ == '__main__':
    main()
