# -*- coding: utf-8 -*-
r"""check_cluster.py — 对两帧的指定区域, 逐差异簇报告"A/B 谁更亮" (墨被去掉还是被补上)。

用法: python check_cluster.py <A.png> <B.png> [--thr 90]
输出: 每个差异簇的 bbox + (A 有墨而 B 没有) 的像素数 / (B 有墨而 A 没有) 的像素数。
"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def clusters(ys, xs, gap=10):
    out = []
    for y, x in sorted(zip(ys.tolist(), xs.tolist())):
        for c in out:
            if y <= c[3] + 2 and x >= c[0] - gap and x <= c[2] + gap:
                c[0] = min(c[0], x); c[2] = max(c[2], x)
                c[1] = min(c[1], y); c[3] = max(c[3], y); c[4] += 1
                break
        else:
            out.append([x, y, x, y, 1])
    return out


def main():
    a = sys.argv[1:]
    ia = np.asarray(Image.open(a[0]).convert('L')).astype(int)
    ib = np.asarray(Image.open(a[1]).convert('L')).astype(int)
    thr = int(a[a.index('--thr') + 1]) if '--thr' in a else 90
    d = ia != ib
    ys, xs = np.where(d)
    print('A = %s' % os.path.basename(a[0]))
    print('B = %s' % os.path.basename(a[1]))
    print('差异像素 %d (阈值 %d)' % (int(d.sum()), thr))
    for c in sorted(clusters(ys, xs), key=lambda c: (c[1], c[0])):
        x0, y0, x1, y1, n = c
        sub = d[y0:y1 + 1, x0:x1 + 1]
        aa = ia[y0:y1 + 1, x0:x1 + 1]
        bb = ib[y0:y1 + 1, x0:x1 + 1]
        a_ink = (aa >= thr) & sub
        b_ink = (bb >= thr) & sub
        print('  簇 x=%d..%d y=%d..%d (%dx%d) %d px | '
              'A 有墨 B 无 = %d ; B 有墨 A 无 = %d'
              % (x0, x1, y0, y1, x1 - x0 + 1, y1 - y0 + 1, n,
                 int(a_ink.sum()), int(b_ink.sum())))
        print('     A 最大亮度 %d / B 最大亮度 %d' % (aa.max(), bb.max()))


if __name__ == '__main__':
    main()
