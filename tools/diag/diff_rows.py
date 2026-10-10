# -*- coding: utf-8 -*-
r"""diff_rows.py — 两图同帧逐行差异统计 (会话工具)
用法: python diff_rows.py <pngA> <pngB> <x0> <y0> <x1> <y1>
"""
import os
import sys

import cv2
import numpy as np


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    a, b = imread_u(sys.argv[1]), imread_u(sys.argv[2])
    x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
    h, w = a.shape[:2]
    sx, sy = w / 640.0, h / 448.0
    A = a[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)].astype(np.int16)
    B = b[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)].astype(np.int16)
    d = (np.abs(A - B).max(axis=2) > 24)
    rows = d.sum(axis=1)
    print('%s  vs  %s  rect=(%d,%d)-(%d,%d)' % (os.path.basename(a.shape and sys.argv[1]),
                                                os.path.basename(sys.argv[2]), x0, y0, x1, y1))
    for i, v in enumerate(rows):
        if v:
            print('  row %2d  y=%6.1f  差异像素=%3d  %s' % (i, y0 + i / sy, v, '#' * min(v, 60)))
    print('  合计差异像素 = %d  行数 = %d' % (rows.sum(), int((rows > 0).sum())))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
