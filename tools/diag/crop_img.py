# -*- coding: utf-8 -*-
r"""crop.py — 截图裁剪/放大 (会话工具, 不入库)
用法: python crop.py <in.png> <out.png> <x0> <y0> <x1> <y1> [scale=3]
坐标 = 原生 640x448 空间 (截图可能已被缩放, 自动换算)。
"""
import os
import sys

import cv2
import numpy as np


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_u(p, img):
    ok, buf = cv2.imencode(os.path.splitext(p)[1], img)
    if ok:
        buf.tofile(p)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[3:7])
    sc = int(sys.argv[7]) if len(sys.argv) > 7 else 3
    img = imread_u(src)
    h, w = img.shape[:2]
    sx, sy = w / 640.0, h / 448.0
    a = img[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)]
    a = cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
    imwrite_u(dst, a)
    print('%s -> %s (%dx%d @%dx)' % (src, dst, a.shape[1], a.shape[0], sc))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
