# -*- coding: utf-8 -*-
r"""reduce_dups.py — 查改写稿里的**重复片段** (规则"原文含改后字"造成的叠字/叠词)

典型病征: `被选拔入` 经 ('选拔','选入') 变成 `被选入入`; `鉴于当时的情况` 经
('鉴于','看当时的情况') 变成 `看当时的情况当时的情况`。
做法: 在 new/<id>.txt 里找「相邻的、长度 1..6 的相同子串」(不含 {WRAP} 与换行)。只读。
"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
NEW = os.path.join(HERE, 'new')
TGT = os.path.join(HERE, 'reduce_targets.json')
SKIP = ('{Warp}', '{WRAP}', '\n')


def main():
    d = json.load(io.open(TGT, encoding='utf-8'))
    n = 0
    for rid in sorted(d):
        p = os.path.join(NEW, rid.replace(':', '_') + '.txt')
        t = io.open(p, encoding='utf-8', newline='').read()
        for L in (1, 2, 3, 4, 6):
            for m in re.finditer(r'(?=(.{%d})\1)' % L, t):
                frag = m.group(1)
                if any(s in frag for s in SKIP):
                    continue
                if L == 1 and frag in '，。、！？“”（）0123456789':
                    continue
                n += 1
                print('%-14s ×%d %r   …%s…' % (rid, L, frag,
                                               t[max(0, m.start() - 12):m.start() + 2 * L + 12]
                                               .replace('\n', '⏎')))
    print('\n共 %d 处重复片段' % n)


if __name__ == '__main__':
    main()
