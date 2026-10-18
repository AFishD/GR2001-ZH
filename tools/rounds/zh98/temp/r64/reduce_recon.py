# -*- coding: utf-8 -*-
r"""reduce_recon.py — 对账: 为什么我的缺字计数和 r64 的 missing_chars.csv 不一样?

两种口径逐条比:
  A) Lead 的 r64_missing_list.py: text_edited.strip(), 剥 {WRAP}, 只算 ord>=0x80 且不在 JSON 的字
  B) reduce_lib 的口径:              text_edited 原样,   剥 {WRAP}, 只算不在 (JSON + ASCII可打印) 的字
打印两者的 (种数/次数) 与**逐条差异**。只读, 不写盘。
"""
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
import tcslib as T                                                    # noqa: E402


def main():
    def scan(strip, ascii_ok):
        cnt, ents = Counter(), {}
        for fn in L.TABLES:
            with io.open(os.path.join(L.TXT, fn), encoding='utf-8-sig', newline='') as f:
                for r in csv.DictReader(f):
                    t = (r.get('text_edited') or '')
                    if strip:
                        t = t.strip()
                    if not t:
                        continue
                    t2 = re.sub(r'\{[Ww][Aa][Rr][Pp]\}', '', t)
                    miss = []
                    for ch in t2:
                        if L.encodable(ch) or ch in miss:
                            continue
                        if not ascii_ok and ord(ch) < 0x80:
                            continue
                        miss.append(ch)
                    if not miss:
                        continue
                    for ch in miss:
                        cnt[ch] += t2.count(ch)
                    ents[r['id']] = len(miss)
        return cnt, ents

    a_cnt, a_ents = scan(True, False)
    b_cnt, b_ents = scan(False, True)
    print('A 口径 (Lead r64): %d 种 / %d 次 / %d 条'
          % (len(a_cnt), sum(a_cnt.values()), len(a_ents)))
    print('B 口径 (本轮)    : %d 种 / %d 次 / %d 条'
          % (len(b_cnt), sum(b_cnt.values()), len(b_ents)))
    print()
    old = {}
    with io.open(os.path.join(HERE, 'missing_chars.csv'), encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            old[r['char']] = int(r['count'])
    print('和 missing_chars.csv 比: %d 行; A 口径差值条目 %d 个'
          % (len(old), sum(1 for k in set(old) | set(a_cnt) if old.get(k) != a_cnt.get(k))))
    diff = [(k, old.get(k, 0), a_cnt.get(k, 0)) for k in sorted(set(old) | set(a_cnt))
            if old.get(k) != a_cnt.get(k)]
    for k, o, n in diff[:15]:
        print('   %r csv=%d now=%d' % (k, o, n))
    print()
    ids = set(a_ents) | set(b_ents)
    for i in sorted(ids):
        if a_ents.get(i) != b_ents.get(i):
            print('   条目 %s: A=%s B=%s' % (i, a_ents.get(i), b_ents.get(i)))


if __name__ == '__main__':
    main()
