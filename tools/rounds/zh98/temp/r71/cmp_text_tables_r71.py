# -*- coding: utf-8 -*-
r"""cmp_text_tables_r71.py — 三张正文表 (GR_ZH114 vs GR_ZH117) 逐列 diff。

目的: 门禁"正文一个字没动"用的是 **盘上字节**(注入器 + 门禁⑦)，这里再把**表**也核一遍，
      并说明 CSV 文件 sha 不同到底差在哪一列 (若是 text_edited/note 这类非盘上列, 与盘无关)。
"""
import csv
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
OUT = os.path.join(HERE, 'cmp_text_tables_r71.txt')


def read(p):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    L = []
    for kind in ('text_long.csv', 'text_long_nowrap.csv', 'text_short.csv'):
        p1 = os.path.join(REPO, 'work', 'builds', 'GR_ZH114', 'text', 'GR_ZH114_' + kind)
        p2 = os.path.join(REPO, 'work', 'builds', 'GR_ZH117', 'text', 'GR_ZH117_' + kind)
        a, b = read(p1), read(p2)
        L.append('== %s ==' % kind)
        L.append('   行数 %d vs %d; 列 = %s' % (len(a), len(b), ','.join(a[0].keys())))
        col_diff = {}
        ex = {}
        same_id = 0
        for x, y in zip(a, b):
            if x['id'] == y['id']:
                same_id += 1
            for c in x:
                if x[c] != y[c]:
                    col_diff[c] = col_diff.get(c, 0) + 1
                    ex.setdefault(c, (x['id'], x[c][:60], y[c][:60]))
        L.append('   id 列相同 %d/%d' % (same_id, len(a)))
        if not col_diff:
            L.append('   ★ 所有列逐格相同 ✓')
        for c, n in sorted(col_diff.items()):
            L.append('   [差异] 列 %-14s %d 格; 例: %s  %r -> %r' % (c, n, *ex[c]))
        L.append('')
    with io.open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(L) + '\n')
    print('\n'.join(L))
    print('wrote', OUT)
    return 0


if __name__ == '__main__':
    sys.exit(main())
