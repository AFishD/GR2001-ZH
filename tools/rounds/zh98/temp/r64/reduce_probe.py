# -*- coding: utf-8 -*-
r"""reduce_probe.py — 找出「B 口径比 A 口径多出来的那个字」到底是什么。只读。"""
import csv
import io
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_lib as L                                                # noqa: E402


def main():
    c = Counter()
    for fn in L.TABLES:
        with io.open(os.path.join(L.TXT, fn), encoding='utf-8-sig', newline='') as f:
            for r in csv.DictReader(f):
                t = r.get('text_edited') or ''
                if not t:
                    continue
                t2 = re.sub(r'\{[Ww][Aa][Rr][Pp]\}', '', t)
                for ch in t2:
                    if ch not in L.AVAIL:
                        c[ch] += 1
    print('全部超范围字 (含 strip 掉的那些): %d 种 / %d 次' % (len(c), sum(c.values())))
    print('前 8 个:')
    for ch, n in c.most_common(8):
        print('   %r U+%04X count=%d  isspace=%s  strip后还在=%s'
              % (ch, ord(ch), n, ch.isspace(), ch in 'x'.join([]) or '?'))
    print()
    print('其中 str.isspace() 为真的 (被 A 口径的 .strip() 吃掉的): %d 种'
          % sum(1 for ch in c if ch.isspace()))
    for ch, n in sorted(((k, v) for k, v in c.items() if k.isspace()),
                        key=lambda x: -x[1]):
        print('   %r U+%04X count=%d' % (ch, ord(ch), n))


if __name__ == '__main__':
    main()
