# -*- coding: utf-8 -*-
r"""ab_menu_probe2.py — 更准的主菜单光标探测: 按行统计"金色"像素, 找**横向金色条**(=选中项)。

用法: python ab_menu_probe2.py <dumpdir> <f0> <f1> [step]
输出: 每个帧的报告 —— 金色条所在 y 区间 + 中心 + 峰值计数; 无可疑条则 '-'.
"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

X0, X1 = 12, 175          # 主菜单左侧列表的横向范围
Y0, Y1 = 60, 300          # 列表纵向范围


def rows_gold(a3):
    r, g, b = (a3[:, :, 0].astype(np.int16), a3[:, :, 1].astype(np.int16),
               a3[:, :, 2].astype(np.int16))
    gold = (r > 150) & (g > 110) & (b < 130) & (r - b > 60)
    return gold[:, X0:X1].sum(axis=1)


def main():
    d, f0, f1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    step = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    for f in range(f0, f1 + 1, step):
        p = os.path.join(d, 'snap_f%08d.png' % f)
        if not os.path.isfile(p):
            continue
        cnt = rows_gold(np.asarray(Image.open(p).convert('RGB')))
        sub = cnt[Y0:Y1]
        mx = int(sub.max())
        if mx < 40:                       # 一整条选中项至少有 ~100 px 宽
            print('%6d  -   (max row gold=%d)' % (f, mx))
            continue
        rows = [Y0 + i for i, v in enumerate(sub) if v >= max(40, mx * 0.5)]
        # 取最长连续段
        best = cur = [rows[0]]
        for y in rows[1:]:
            if y - cur[-1] <= 2:
                cur.append(y)
            else:
                if len(cur) > len(best):
                    best = cur
                cur = [y]
        if len(cur) > len(best):
            best = cur
        print('%6d  bar y=%3d..%3d  h=%2d  peak=%3d' % (f, best[0], best[-1],
                                                        best[-1] - best[0] + 1, mx))


if __name__ == '__main__':
    main()
