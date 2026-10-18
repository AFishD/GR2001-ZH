# -*- coding: utf-8 -*-
r"""zx_cmp_shots.py — 两张盘的实机截图逐像素对比 + cdvd.log 读取量对比

用法:
  python zx_cmp_shots.py <dumpA> <dumpB> [--region ABS_OFF LEN] [--label X]
"""
import argparse
import glob
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image                                                 # noqa: E402
import numpy as np                                                    # noqa: E402

SEC = 2048


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--region', nargs=2, type=lambda s: int(s, 0), default=None)
    ap.add_argument('--label', default='COMMON.PAK 字库区')
    a = ap.parse_args()
    fa = {os.path.basename(p): p for p in glob.glob(os.path.join(a.a, 'snap_*.png'))}
    fb = {os.path.basename(p): p for p in glob.glob(os.path.join(a.b, 'snap_*.png'))}
    common = sorted(set(fa) & set(fb))
    only_a = sorted(set(fa) - set(fb))
    only_b = sorted(set(fb) - set(fa))
    print('A = %s : %d 张' % (a.a, len(fa)))
    print('B = %s : %d 张' % (a.b, len(fb)))
    print('同名可比 %d 张 ; 仅 A %d 张 %s ; 仅 B %d 张 %s'
          % (len(common), len(only_a), only_a[:4], len(only_b), only_b[:4]))
    same = 0
    diff = []
    for n in common:
        ba, bb = open(fa[n], 'rb').read(), open(fb[n], 'rb').read()
        if ba == bb:
            same += 1
            continue
        ia = np.asarray(Image.open(fa[n]).convert('RGB')).astype(np.int16)
        ib = np.asarray(Image.open(fb[n]).convert('RGB')).astype(np.int16)
        if ia.shape == ib.shape:
            d = int((np.abs(ia - ib).sum(axis=2) > 0).sum())
        else:
            d = -1
        diff.append((n, len(ba), len(bb), d))
    print('★ 逐字节相同 %d / %d ; 不同 %d' % (same, len(common), len(diff)))
    for (n, la, lb, d) in diff[:12]:
        print('    %s : 字节 %d vs %d ; 像素差异 %s' % (n, la, lb, d))
    if a.region:
        off, ln = a.region
        print('\ncdvd.log 读取量对比: %s ISO 0x%X..0x%X (%d B)' % (a.label, off, off + ln, ln))
        for tag, d in (('A', a.a), ('B', a.b)):
            p = os.path.join(d, 'cdvd.log')
            if not os.path.exists(p):
                print('  %s: 没有 cdvd.log' % tag)
                continue
            lo, hi = off // SEC, (off + ln + SEC - 1) // SEC
            ev, inreg = 0, []
            with open(p, encoding='utf-8', errors='replace') as f:
                for line in f:
                    q = line.split()
                    if len(q) != 2:
                        continue
                    ev += 1
                    try:
                        l = int(q[1])
                    except ValueError:
                        continue
                    if lo <= l < hi:
                        inreg.append(l)
            lsns = sorted(set(inreg))
            inter = sum(max(0, min(l * SEC + SEC, off + ln) - max(l * SEC, off)) for l in lsns)
            print('  %s: 全盘事件 %d ; 区间内事件 %d ; 去重扇区 %d ; 求交覆盖 %d B'
                  % (tag, ev, len(inreg), len(lsns), inter))


if __name__ == '__main__':
    main()
