# -*- coding: utf-8 -*-
r"""ab_ascii.py — 用**多档灰度**打印帧的一块区域 (看清文字/底框的明暗)。

用法: python ab_ascii.py <frame.png> x0 x1 y0 y1 [--mode gray|ink]
  gray: 用 0-9 表示灰度分档 (0=最暗, 9=最亮)
  ink : 三档 . : + #  (<64 / 64..159 / >=160)
"""
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    p = sys.argv[1]
    x0, x1, y0, y1 = (int(v) for v in sys.argv[2:6])
    mode = sys.argv[sys.argv.index('--mode') + 1] if '--mode' in sys.argv else 'gray'
    g = np.asarray(Image.open(p).convert('L')).astype(int)
    print('%s  区域 x=%d..%d y=%d..%d  mode=%s' % (p.split('\\')[-1], x0, x1, y0, y1, mode))
    for y in range(y0, y1):
        if mode == 'gray':
            ln = ''.join(str(min(9, g[y, x] // 26)) for x in range(x0, x1))
        else:
            ln = ''.join('.' if g[y, x] < 64 else ('+' if g[y, x] < 160 else '#')
                         for x in range(x0, x1))
        print('%4d |%s|' % (y, ln))


if __name__ == '__main__':
    main()
