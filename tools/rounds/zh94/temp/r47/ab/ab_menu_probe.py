# -*- coding: utf-8 -*-
r"""ab_menu_probe.py — 只读诊断: 逐帧找**主菜单高亮条**(金色)的 y 位置。

用法: python ab_menu_probe.py <dumpdir> <f0> <f1> [step] [x0 x1 y0 y1]

金色高亮 ≈ R>150 & G>110 & B<120。打印每帧高亮条的 y 范围 + 高度 ⇒
一眼看出"光标在第几项"、"按了几次下移/上移登记成功"、"菜单是夹住还是回绕"。
"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def main():
    a = sys.argv[1:]
    d = a[0]
    f0, f1 = int(a[1]), int(a[2])
    step = int(a[3]) if len(a) > 3 else 100
    x0, x1, y0, y1 = ([int(v) for v in a[4:8]] if len(a) >= 8 else [8, 180, 50, 260])
    for f in range(f0, f1 + 1, step):
        p = os.path.join(d, 'snap_f%08d.png' % f)
        if not os.path.isfile(p):
            continue
        a3 = np.asarray(Image.open(p).convert('RGB'))
        r, g, b = (a3[:, :, 0].astype(np.int16), a3[:, :, 1].astype(np.int16),
                   a3[:, :, 2].astype(np.int16))
        gold = (r > 150) & (g > 110) & (b < 130) & (r - b > 60)
        sub = gold[y0:y1, x0:x1]
        ys, xs = np.where(sub)
        if len(ys) == 0:
            print('%6d  -' % f)
            continue
        print('%6d  y=%3d..%3d (h=%2d)  x=%3d..%3d  n=%4d'
              % (f, y0 + ys.min(), y0 + ys.max(), ys.max() - ys.min() + 1,
                 x0 + xs.min(), x0 + xs.max(), len(ys)))


if __name__ == '__main__':
    main()
