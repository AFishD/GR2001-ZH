# -*- coding: utf-8 -*-
r"""screens.py -- 把一次手臂的快照序列压成"画面段"时间线 (按帧号顺序)。

每段 = 连续若干张**逐字节相同**的 PNG。输出: <dir>\SCREENS.txt
用途: ① 给报告提供"什么帧号是什么界面"的客观骨架
      ② 直接量"同一画面最长持续多少帧"= 空转/静止的指纹

用法: python work\builds\GR_FPS\tools\screens.py <dumpdir> <snap_interval> [--min-n 2]
"""
import hashlib
import io
import os
import re
import sys

RX = re.compile(r'^snap_f(\d+)\.png$')


def main():
    d = os.path.abspath(sys.argv[1])
    iv = int(sys.argv[2])
    min_n = 2
    if '--min-n' in sys.argv:
        min_n = int(sys.argv[sys.argv.index('--min-n') + 1])

    items = []
    for fn in os.listdir(d):
        m = RX.match(fn)
        if not m:
            continue
        p = os.path.join(d, fn)
        h = hashlib.sha1(open(p, 'rb').read()).hexdigest()
        items.append((int(m.group(1)), os.path.getsize(p), h))
    items.sort()

    runs = []
    start = 0
    for i in range(1, len(items)):
        if items[i][2] != items[i - 1][2]:
            runs.append((start, i - 1))
            start = i
    runs.append((start, len(items) - 1))

    out = os.path.join(d, 'SCREENS.txt')
    with io.open(out, 'w', encoding='utf-8') as f:
        f.write('# dir=%s  snap_interval=%d  snaps=%d  distinct=%d  runs=%d\n'
                % (d, iv, len(items), len(set(x[2] for x in items)), len(runs)))
        f.write('# %-10s %-10s %6s %8s  %s\n'
                % ('f_from', 'f_to', 'n', 'frames', 'sha1_8/size'))
        for (a, b) in runs:
            n = b - a + 1
            if n < min_n:
                continue
            f.write('  %-10d %-10d %6d %8d  %s/%d\n'
                    % (items[a][0], items[b][0], n, n * iv,
                       items[a][2][:8], items[a][1]))
    print('wrote %s (%d runs total, %d runs with n>=%d)' % (out, len(runs), 
          sum(1 for (a, b) in runs if b - a + 1 >= min_n), min_n))
    # 最长段
    best = max(runs, key=lambda ab: ab[1] - ab[0])
    print('  longest same-screen run: %d frames (f%d..f%d)'
          % ((best[1] - best[0] + 1) * iv, items[best[0]][0], items[best[1]][0]))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
