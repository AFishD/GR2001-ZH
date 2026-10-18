# -*- coding: utf-8 -*-
r"""snapdiff_all.py — 两盘同 nav 全快照逐帧比对 (会话工具)
用法: python snapdiff_all.py <dirA> <dirB> [thr]
"""
import os
import sys

import cv2
import numpy as np


def imread_u(p):
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def main():
    da, db = sys.argv[1], sys.argv[2]
    thr = int(sys.argv[3]) if len(sys.argv) > 3 else 12
    fa = sorted(f for f in os.listdir(da) if f.startswith('snap_') and f.endswith('.png'))
    fb = set(os.listdir(db))
    same = diff = missing = 0
    rows = []
    for f in fa:
        if f not in fb:
            missing += 1
            continue
        a, b = imread_u(os.path.join(da, f)), imread_u(os.path.join(db, f))
        if a is None or b is None or a.shape != b.shape:
            diff += 1
            rows.append((f, -1, 'shape'))
            continue
        mx = int(np.abs(a.astype(np.int16) - b.astype(np.int16)).max())
        n = int((np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2) > thr).sum())
        if n == 0:
            same += 1
        else:
            diff += 1
            rows.append((f, n, 'maxch=%d' % mx))
    print('快照 %d 个: 逐像素一致 %d; 有差异 %d; 缺帧 %d' % (len(fa), same, diff, missing))
    for f, n, extra in rows[:14]:
        print('   %s  差异px=%d  %s' % (f, n, extra))
    if len(rows) > 14:
        print('   ...(共 %d 帧有差异)' % len(rows))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
