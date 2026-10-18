# -*- coding: utf-8 -*-
r"""xcheck_r63.py — 新可注入表 vs round62 view 表 (zh-main 那 145 行) 逐列对照。

只读。用来证明"两张表说的是同一批属性、同一个偏移"。
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

NEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH110', 'inject_titles',
                   'GR_ZH109_text_sf_titles.csv')
VIEW = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_r62',
                    'GR_ZH109_view_sf_titles.csv')
COLS = ('tag', 'entry_index', 'offset', 'len_bytes', 'text_zh')


def rows(p):
    return list(csv.DictReader(open(p, encoding='utf-8-sig')))


def main():
    new = rows(NEW)
    view = [r for r in rows(VIEW) if r['copy_role'] == 'zh-main']
    view = [dict(r, text_zh=r['text']) for r in view]
    print('新表 %d 行 / view 表 zh-main %d 行' % (len(new), len(view)))
    bad = 0
    for i, (a, b) in enumerate(zip(new, view), 1):
        ka = (a['tag'], a['entry_index'], a['offset'], a['len_bytes'], a['text_zh'])
        kb = (b['tag'], b['entry_index'].zfill(0) and ('A%04d' % int(b['entry_index'])),
              b['offset'], b['len_bytes'], b['text_zh'])
        if ka != kb:
            bad += 1
            if bad <= 5:
                print('  !! #%d\n     新: %s\n     旧: %s' % (i, ka, kb))
    print('逐行一致 = %s (%d 处不符)' % ('✓' if bad == 0 else '✗', bad))
    # 也核对 container / lang / copy_role
    c1 = set(r['container'] for r in new)
    c2 = set(r['container'] for r in view)
    print('container: %s vs %s  %s' % (c1, c2, '✓' if c1 == c2 else '✗'))
    print('text_en 空行 = %d' % sum(1 for r in new if not r['text_en']))


if __name__ == '__main__':
    main()
