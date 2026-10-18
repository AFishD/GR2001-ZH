# -*- coding: utf-8 -*-
r"""make_work_tables.py — 因原表被 Excel 占用: 复制多表到 text_work/ 并在那里把 × 换成 x
   原表 (work/builds/GR_ZH92/text/) 保持不动; 构筑/注入从 text_work/ 走。"""
import csv
import io
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
DST = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text_work')
TIMES, LOWX = '\u00d7', 'x'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    os.makedirs(DST, exist_ok=True)
    total = 0
    for name in sorted(os.listdir(SRC)):
        if not name.endswith('.csv'):
            continue
        s, d = os.path.join(SRC, name), os.path.join(DST, name)
        shutil.copyfile(s, d)
        with io.open(d, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
        n = 0
        for r in rows:
            c = r['text_edited'].count(TIMES)
            if c:
                r['text_edited'] = r['text_edited'].replace(TIMES, LOWX)
                n += c
        if n:
            with io.open(d, 'w', encoding='utf-8-sig', newline='') as f:
                w = csv.DictWriter(f, fieldnames=cols, lineterminator='\r\n',
                                   quoting=csv.QUOTE_MINIMAL)
                w.writeheader()
                w.writerows(rows)
        total += n
        print('  %-34s %5d 条   × → x: %d 处' % (name, len(rows), n))
    print('合计替换 %d 处' % total)
    print('工作副本目录:', os.path.relpath(DST, REPO))


if __name__ == '__main__':
    main()
