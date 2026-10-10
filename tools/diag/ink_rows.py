# -*- coding: utf-8 -*-
r"""ink_rows.py — 统计截图某矩形内逐行墨迹 (会话工具)
用法: python ink_rows.py <png> <x0> <y0> <x1> <y1> [thr]
坐标 = 原生 640x448 (按截图尺寸换算); thr = 亮度阈值 (缺省取"背景+文字"自动二分)。
输出: 每行墨像素数 + 墨带范围/质心。
"""
import os
import sys

import cv2
import numpy as np


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    src = sys.argv[1]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6])
    img = imread_u(src)
    h, w = img.shape[:2]
    sx, sy = w / 640.0, h / 448.0
    a = img[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)]
    g = a.mean(axis=2)
    thr = float(sys.argv[6]) if len(sys.argv) > 6 else (float(g.min()) + float(g.max())) / 2.0
    dark = '--dark' in sys.argv          # 深字浅底 (高亮黄框) 用 --dark
    mask = (g < thr) if dark else (g > thr)
    rows = mask.sum(axis=1)
    idx = [i for i, v in enumerate(rows) if v > 0]
    print('%s  rect=(%d,%d)-(%d,%d) 局部 %dx%d  thr=%.1f' % (src, x0, y0, x1, y1,
                                                             a.shape[1], a.shape[0], thr))
    for i, v in enumerate(rows):
        print('  row %2d  y=%6.1f  ink=%3d  %s' % (i, y0 + i / sy, v, '#' * min(v, 80)))
    if idx:
        tot = rows.sum()
        cy = sum(i * v for i, v in enumerate(rows)) / max(tot, 1)
        print('  墨带 rows[%d..%d] = 原生 y[%.1f..%.1f]  质心 y=%.2f  墨像素=%d'
              % (idx[0], idx[-1], y0 + idx[0] / sy, y0 + idx[-1] / sy, y0 + cy / sy, tot))
    else:
        print('  无墨 (阈值过高?)')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
