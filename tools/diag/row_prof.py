# -*- coding: utf-8 -*-
r"""row_prof.py — 打印区域逐行墨量 (会话工具)
用法: python row_prof.py <pngA> <pngB> <x0> <y0> <x1> <y1> [thr] [--dark]
"""
import os
import sys

import cv2
import numpy as np


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def prof(path, rect, thr, dark):
    x0, y0, x1, y1 = rect
    img = imread_u(path)
    h, w = img.shape[:2]
    sx, sy = w / 640.0, h / 448.0
    a = img[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)].mean(axis=2)
    m = (a < thr) if dark else (a > thr)
    return m.sum(axis=1), sy


def main():
    a, b = sys.argv[1], sys.argv[2]
    rect = tuple(int(v) for v in sys.argv[3:7])
    thr = float(sys.argv[7]) if len(sys.argv) > 7 else 150.0
    dark = '--dark' in sys.argv
    pa, sy = prof(a, rect, thr, dark)
    pb, _ = prof(b, rect, thr, dark)
    print('rect=%s thr=%.0f %s' % (rect, thr, 'dark' if dark else 'bright'))
    print('%6s %8s %6s %6s' % ('row', 'nativeY', 'A', 'B'))
    for i, (x, y) in enumerate(zip(pa, pb)):
        mark = '  <<<' if x != y else ''
        print('%6d %8.1f %6d %6d%s' % (i, rect[1] + i / sy, x, y, mark))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
