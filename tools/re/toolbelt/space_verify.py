# -*- coding: utf-8 -*-
r"""space_verify.py -- 两张盘的全量逐字节差异图（只读）。用于独立复核探针盘"只改了我说的那些"。"""
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
SEC = 2048
MENU_LBA = 776286
base = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')


def diffmap(p2, label):
    p1 = base
    s1, s2 = os.path.getsize(p1), os.path.getsize(p2)
    print('=== %s : %s ===' % (label, os.path.basename(p2)))
    print('  size %d vs %d  %s' % (s1, s2, '相同' if s1 == s2 else '★不同★'))
    assert s1 == s2
    runs = []
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        off = 0
        cur = None
        while True:
            b1 = f1.read(1 << 24)
            b2 = f2.read(1 << 24)
            if not b1:
                break
            a1 = np.frombuffer(b1, dtype=np.uint8)
            a2 = np.frombuffer(b2, dtype=np.uint8)
            d = np.flatnonzero(a1 != a2)
            if d.size:
                # 归并到 isl 区间
                starts = np.concatenate(([0], np.flatnonzero(np.diff(d) > 4096) + 1))
                ends = np.concatenate((np.flatnonzero(np.diff(d) > 4096), [d.size - 1]))
                for s, e in zip(starts, ends):
                    runs.append((off + int(d[s]), off + int(d[e]), int(d[e]) - int(d[s]) + 1,
                                 int(e - s + 1)))
            off += len(b1)
    tot = sum(r[3] for r in runs)
    print('  差异区段 %d 个, 差异字节合计 %d' % (len(runs), tot))
    for s, e, span, n in sorted(runs, key=lambda z: -z[3])[:20]:
        menu_off = s - MENU_LBA * SEC if s >= MENU_LBA * SEC else None
        print('    ISO[0x%09X..0x%09X] 跨度=%-10d 差异=%-9d %s' %
              (s, e, span, n,
               ('MENU.IMG+0x%X' % menu_off) if menu_off is not None and menu_off < 0x37A1000
               else ''))
    return runs


def main():
    for d, tag in (('GR_TEST_SPACE_LEN', '探针A'), ('GR_TEST_SPACE_PAK', '探针B')):
        p = os.path.join(REPO, 'work', 'builds', d, '%s.iso' % d)
        if os.path.isfile(p):
            diffmap(p, tag)
            print()
        else:
            print('(%s 不存在)' % p)


main()
