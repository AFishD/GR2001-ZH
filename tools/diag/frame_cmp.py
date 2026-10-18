# -*- coding: utf-8 -*-
r"""frame_cmp.py — 两盘同帧全屏对比 (均值/最大通道差 + 差异行) (会话工具)
用法: python frame_cmp.py <pngA> <pngB> [diffthr]
无阈值版: 逐像素通道差统计 (捕捉变色/亮度变化, 不只形状差)。
"""
import os
import sys

import cv2
import numpy as np


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    a, b = imread_u(sys.argv[1]), imread_u(sys.argv[2])
    thr = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    if a.shape != b.shape:
        print('尺寸不同: %s vs %s' % (a.shape, b.shape))
        return
    d = np.abs(a.astype(np.int16) - b.astype(np.int16))  # H,W,3
    mx = d.max(axis=2)
    print('%s\n%s' % (sys.argv[1], sys.argv[2]))
    print('  逐像素通道差: max=%d  mean=%.3f  >%d 的像素=%d (%.3f%%)'
          % (mx.max(), float(mx.mean()), thr, int((mx > thr).sum()),
             100.0 * float((mx > thr).sum()) / mx.size))
    rows = (mx > thr).sum(axis=1)
    bands = []
    st = None
    for i, v in enumerate(rows):
        if v > 0 and st is None:
            st = i
        elif v == 0 and st is not None:
            bands.append((st, i - 1, int(rows[st:i].sum())))
            st = None
    if st is not None:
        bands.append((st, len(rows) - 1, int(rows[st:].sum())))
    for st, en, n in bands[:24]:
        sega = a[st:en + 1].reshape(-1, 3).mean(axis=0)
        segb = b[st:en + 1].reshape(-1, 3).mean(axis=0)
        print('    行带 y[%d..%d] 差异px=%d  BGR均值 A=%s B=%s (Δ=%s)'
              % (st, en, n, np.round(sega, 1), np.round(segb, 1), np.round(segb - sega, 1)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
