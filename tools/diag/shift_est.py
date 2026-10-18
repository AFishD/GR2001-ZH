# -*- coding: utf-8 -*-
r"""shift_est.py — 估计两图某区域的竖直位移 (相位相关, 亚像素) (会话工具)
用法: python shift_est.py <pngA> <pngB> <x0> <y0> <x1> <y1>
正数 = B 相对 A 向下位移 (px, 原生 640x448 尺度)
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
    A = a[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)]
    B = b[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)]
    ga = cv2.cvtColor(A, cv2.COLOR_BGR2GRAY).astype(np.float32)
    gb = cv2.cvtColor(B, cv2.COLOR_BGR2GRAY).astype(np.float32)
    win = cv2.createHanningWindow((ga.shape[1], ga.shape[0]), cv2.CV_32F)
    (dx, dy), resp = cv2.phaseCorrelate(ga, gb, win)
    print('%s → %s  区域(%d,%d)-(%d,%d)' % (os.path.basename(os.path.dirname(os.path.dirname(sys.argv[1]))),
                                            os.path.basename(os.path.dirname(os.path.dirname(sys.argv[2]))),
                                            x0, y0, x1, y1))
    print('  相位相关: Δx=%+.2f 截图px  Δy=%+.2f 截图px  →  Δy=%+.2f 原生px (置信 %.3f)'
          % (dx, dy, dy / sy, resp))
    # 亚像素最小二乘 (仅竖直): 用整数位移 + 抛物线拟合
    best = None
    for d in range(-6, 7):
        a2 = ga[max(0, d):ga.shape[0] + min(0, d), :]
        b2 = gb[max(0, -d):gb.shape[0] + min(0, -d), :]
        if a2.shape != b2.shape or a2.size == 0:
            continue
        err = float(np.mean((a2 - b2) ** 2))
        if best is None or err < best[1]:
            best = (d, err)
    print('  整数最优位移 = %+d 截图px = %+.2f 原生px' % (best[0], best[0] / sy))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
