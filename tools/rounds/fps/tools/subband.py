# -*- coding: utf-8 -*-
r"""subband.py -- 任意帧区间的局部帧率 (与 bands.py 同一原理, 但区间从命令行给)。

用法: python work\builds\GR_FPS\tools\subband.py <dir> "f0-f1" ["f0-f1" ...]
"""
import os
import re
import sys

RX = re.compile(r'^snap_f(\d+)\.png$')


def main():
    d = os.path.abspath(sys.argv[1])
    snaps = []
    for fn in os.listdir(d):
        m = RX.match(fn)
        if m:
            snaps.append((int(m.group(1)), os.stat(os.path.join(d, fn)).st_mtime))
    snaps.sort()
    base = snaps[0]
    print('=== %s ===' % os.path.basename(d))
    for spec in sys.argv[2:]:
        f0, f1 = (int(x) for x in spec.replace('f', '').split('-'))
        sel = [s for s in snaps if f0 <= s[0] <= f1]
        if len(sel) < 2:
            print('  %-14s 快照不足 (%d)' % (spec, len(sel)))
            continue
        frames = sel[-1][0] - sel[0][0]
        span = sel[-1][1] - sel[0][1]
        print('  %-14s n=%2d  f%d..f%d  frames=%5d  span=%7.3f s  fps=%8.2f  ms/frame=%6.2f'
              % (spec, len(sel), sel[0][0], sel[-1][0], frames, span,
                 frames / span, 1000.0 * span / frames))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
