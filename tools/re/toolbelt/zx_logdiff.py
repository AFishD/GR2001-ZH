# -*- coding: utf-8 -*-
r"""zx_logdiff.py — 两份 emulog 的"首处分歧"定位 (去掉时间戳后逐行比对)

用法: python zx_logdiff.py <A.log> <B.log> [--skip-needle]
"""
import argparse
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
TS = re.compile(r'^\[\s*([0-9.]+)\]\s?')


def norm(p, skip_needle=True):
    out = []
    with open(p, encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = TS.match(ln)
            t = float(m.group(1)) if m else 0.0
            body = TS.sub('', ln).rstrip('\n')
            if skip_needle and 'needle' in body:
                continue
            if 'GSScreenshot' in body:
                continue
            out.append((t, body))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--skip-needle', action='store_true', default=True)
    ap.add_argument('--show', type=int, default=25)
    x = ap.parse_args()
    A, B = norm(x.a), norm(x.b)
    print('A 行 %d ; B 行 %d' % (len(A), len(B)))
    i = 0
    while i < min(len(A), len(B)) and A[i][1] == B[i][1]:
        i += 1
    print('★ 首个不同在第 %d 行:' % (i + 1))
    for k in range(max(0, i - 6), min(len(A), i + x.show)):
        mark = '   ' if k < i else '>> '
        print('%sA[%5d t=%7.3f] %s' % (mark, k + 1, A[k][0], A[k][1][:150]))
    print('-' * 70)
    for k in range(max(0, i - 6), min(len(B), i + x.show)):
        mark = '   ' if k < i else '>> '
        print('%sB[%5d t=%7.3f] %s' % (mark, k + 1, B[k][0], B[k][1][:150]))


if __name__ == '__main__':
    main()
