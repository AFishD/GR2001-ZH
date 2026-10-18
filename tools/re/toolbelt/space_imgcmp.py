# -*- coding: utf-8 -*-
r"""space_imgcmp.py -- 两张探针盘的截图逐像素对比（只读）。"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
A = os.path.join(REPO, 'work', 'builds', 'GR_TEST_SPACE_LEN', 'temp', 'dump_lenA')
B = os.path.join(REPO, 'work', 'builds', 'GR_TEST_SPACE_PAK', 'temp', 'dump_pakB')


def load(p):
    return np.asarray(Image.open(p).convert('RGB')).astype(np.int16)


def main():
    pairs = [('lenA_page.png', 'pakB_page.png', '访谈页'),
             ('lenA_pg0_down.png', 'pakB_pg0_down.png', 'pg0 down'),
             ('lenA_pg1_down.png', 'pakB_pg1_down.png', 'pg1 down'),
             ('lenA_pg2_right.png', 'pakB_pg2_right.png', 'pg2 right'),
             ('lenA_pg3_l1.png', 'pakB_pg3_l1.png', 'pg3 l1'),
             ('lenA_pg4_r1.png', 'pakB_pg4_r1.png', 'pg4 r1'),
             ('lenA_pg5_left.png', 'pakB_pg5_left.png', 'pg5 left')]
    print('== 探针A(仅改 ISO 目录长度) vs 探针B(+搬 2 条 +PAK 长 41440) ==')
    for fa, fb, tag in pairs:
        pa, pb = os.path.join(A, fa), os.path.join(B, fb)
        if not (os.path.isfile(pa) and os.path.isfile(pb)):
            print('  %-12s (缺文件)' % tag)
            continue
        ia, ib = load(pa), load(pb)
        if ia.shape != ib.shape:
            print('  %-12s 尺寸不同 %s vs %s' % (tag, ia.shape, ib.shape))
            continue
        d = np.abs(ia - ib).max(axis=2)
        n = int((d > 0).sum())
        print('  %-12s %s  不同像素 = %-8d (%.4f%%)  最大差 = %d'
              % (tag, ia.shape, n, 100.0 * n / (ia.shape[0] * ia.shape[1]), int(d.max())))
    # 也与各自的 boot 期截图比一下（非同帧，仅记录）
    print('\n== 目录里的截图清单 ==')
    for d in (A, B):
        fs = sorted(x for x in os.listdir(d) if x.endswith('.png'))
        print('  %-14s %d 张: %s' % (os.path.basename(d), len(fs), fs[:8]))


main()
