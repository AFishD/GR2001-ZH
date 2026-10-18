# -*- coding: utf-8 -*-
r"""r69_imgdiff.py — 两张 PNG 的差异定位 (外接框 + 分区计数 + 差异像素可视化)。

用法: python r69_imgdiff.py <A.png> <B.png> [--out diff.png] [--tol 0]
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--out', default=None)
    ap.add_argument('--tol', type=int, default=0)
    a = ap.parse_args()
    import cv2
    import numpy as np

    def rd(p):
        return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
    ia, ib = rd(a.a), rd(a.b)
    print('A %s %s' % (os.path.basename(a.a), ia.shape))
    print('B %s %s' % (os.path.basename(a.b), ib.shape))
    if ia.shape != ib.shape:
        print('!! 尺寸不同'); return 1
    d = np.abs(ia.astype(np.int16) - ib.astype(np.int16)).max(axis=2)
    mask = d > a.tol
    n = int(mask.sum())
    print('差异像素 = %d / %d (%.4f%%)' % (n, mask.size, 100.0 * n / mask.size))
    if n == 0:
        return 0
    ys, xs = np.nonzero(mask)
    print('外接框 = x[%d..%d] y[%d..%d]  (宽 %d 高 %d)'
          % (xs.min(), xs.max(), ys.min(), ys.max(),
             xs.max() - xs.min() + 1, ys.max() - ys.min() + 1))
    # 分 8 条横带统计
    h = ia.shape[0]
    for i in range(8):
        y0, y1 = h * i // 8, h * (i + 1) // 8
        c = int(mask[y0:y1].sum())
        if c:
            print('   y %3d..%3d : %6d 像素 (%.0f%%)' % (y0, y1 - 1, c, 100.0 * c / n))
    # 差异直方 (强度)
    vals = d[mask]
    print('  差异强度: 最大 %d 中位 %d ; 强度<=8 的占 %.1f%%'
          % (vals.max(), int(np.median(vals)), 100.0 * float((vals <= 8).sum()) / len(vals)))
    if a.out:
        viz = ia.copy()
        viz[mask] = (0, 0, 255)
        ok, buf = cv2.imencode('.png', viz)
        buf.tofile(a.out)
        print('  → %s (差异像素涂红)' % a.out)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
