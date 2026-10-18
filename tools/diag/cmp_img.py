# -*- coding: utf-8 -*-
r"""cmp3.py — 多盘同帧对照图 (会话工具)
用法: python cmp3.py <out.png> <x0> <y0> <x1> <y1> <scale> <标签>:<png> [<标签>:<png> ...]
坐标 = 原生 640x448; 图像按截图实际尺寸自动换算。
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
    out = sys.argv[1]
    x0, y0, x1, y1, sc = (int(v) for v in sys.argv[2:7])
    rows = []
    for spec in sys.argv[7:]:
        label, path = spec.split(':', 1)
        img = imread_u(path)
        h, w = img.shape[:2]
        sx, sy = w / 640.0, h / 448.0
        a = img[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)]
        a = cv2.resize(a, None, fx=sc, fy=sc, interpolation=cv2.INTER_NEAREST)
        bar = np.full((26, a.shape[1], 3), 32, np.uint8)
        cv2.putText(bar, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
        rows.append(np.vstack([bar, a]))
    wmin = min(r.shape[1] for r in rows)
    rows = [r[:, :wmin] for r in rows]
    img = np.vstack(rows)
    imwrite_u(out, img)
    print('%s  (%dx%d)' % (out, img.shape[1], img.shape[0]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
