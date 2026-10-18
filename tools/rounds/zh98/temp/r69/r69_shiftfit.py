# -*- coding: utf-8 -*-
r"""r69_shiftfit.py — 判断两帧的差异是不是"纯水平位移" (滚动条/跑马灯相位差)。

对给定 y 带, 在 [-R, R] 内搜索最佳水平位移 dx, 使 A(裁切后) 与 B 的差异最小;
若最佳 dx 处的差异像素相对 dx=0 大幅下降 (例如 <10%), 说明差异 = 相位差, 不是内容差。

用法: python r69_shiftfit.py <A.png> <B.png> <y0> <y1> [R]
"""
import sys


def main():
    a, b, y0, y1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    R = int(sys.argv[5]) if len(sys.argv) > 5 else 24
    import cv2
    import numpy as np

    def rd(p):
        return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
    ia, ib = rd(a), rd(b)
    A = ia[y0:y1].astype(np.int16)
    B = ib[y0:y1].astype(np.int16)
    print('  y 带 %d..%d ; 搜索 dx ∈ [-%d, %d]' % (y0, y1 - 1, R, R))
    base = None
    best = []
    for dx in range(-R, R + 1):
        if dx >= 0:
            x, y = A[:, dx:], B[:, :A.shape[1] - dx]
        else:
            x, y = A[:, :A.shape[1] + dx], B[:, -dx:]
        n = int((np.abs(x - y).max(axis=2) > 0).sum())
        if dx == 0:
            base = n
        best.append((n, dx))
    best.sort()
    print('  dx=0        差异像素 = %d' % base)
    print('  最佳 dx=%+3d 差异像素 = %d  (降到 %.1f%%)'
          % (best[0][1], best[0][0], 100.0 * best[0][0] / max(base, 1)))
    print('  前 5 名: %s' % ['dx=%+d:%d' % (d, n) for n, d in best[:5]])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
