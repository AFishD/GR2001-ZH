# -*- coding: utf-8 -*-
"""changes_only_r68.py — 生成"只看改动"的紧凑表 (给报告/用户复核用)."""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'titles_changes.csv')
REVIEW = os.path.join(HERE, 'titles_review.csv')


def main():
    with io.open(REVIEW, 'r', encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    keep = [r for r in rows if r['text_zh'] != r['suggest']]
    cols = ['id', 'tag', 'text_en', 'text_zh', 'suggest', 'n_chars_old', 'n_chars_new',
            'verdict', 'reason']
    with io.open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')
        w.writerow(cols)
        for r in keep:
            w.writerow([r[c] for c in cols])
    print('wrote %s (%d 行)' % (OUT, len(keep)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
