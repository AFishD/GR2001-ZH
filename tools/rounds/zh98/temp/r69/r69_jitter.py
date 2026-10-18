# -*- coding: utf-8 -*-
r"""r69_jitter.py — 三盘逐帧像素差异对照表: 把"补丁差异"与"跑批抖动"分开。

A = GR_ZH111 (colleague 的 run, dump_hook111)
B = GR_ZH112 (colleague 的 run, dump_hook112)   ← A/B 是**两次独立跑批**, 参照系
C = GR_ZH115 (本轮 run, dump_z115sf / dump_z115brief)

若 |A-B| == |A-C| (同一帧、差异像素数相同), 说明 A 与 C 的差异 = 跑批抖动 (与补丁无关);
若 |A-C| > |A-B|, 才是补丁引入的差异。

用法: python r69_jitter.py <A目录> <B目录> <C目录> [--pattern snap_f]
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('c')
    ap.add_argument('--pattern', default='snap_f')
    ap.add_argument('--out', default=None)
    x = ap.parse_args()
    import cv2
    import numpy as np

    def rd(p):
        return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)

    def n(a, b):
        if a is None or b is None or a.shape != b.shape:
            return None
        return int((a != b).any(axis=2).sum())

    fa = sorted(f for f in os.listdir(x.a) if f.startswith(x.pattern) and f.endswith('.png'))
    fb = set(os.listdir(x.b))
    fc = set(os.listdir(x.c))
    rows, verdict = [], []
    for fn in fa:
        if fn not in fc:
            continue
        ia = rd(os.path.join(x.a, fn))
        ib = rd(os.path.join(x.b, fn)) if fn in fb else None
        ic = rd(os.path.join(x.c, fn))
        d_ab, d_ac = n(ia, ib), n(ia, ic)
        tag = ''
        if d_ab is not None and d_ac is not None:
            if d_ac <= d_ab:
                tag = '抖动(与 A↔B 同级或更小)'
                verdict.append(True)
            else:
                tag = '★ 超过抖动 = 补丁差异?'
                verdict.append(False)
        rows.append((fn, d_ab, d_ac, tag))
    print('%-24s %10s %10s  %s' % ('帧', '|A-B|(抖动)', '|A-C|', '判读'))
    for fn, ab, ac, tag in rows:
        print('%-24s %10s %10s  %s' % (fn, '-' if ab is None else ab,
                                       '-' if ac is None else ac, tag))
    if rows:
        eq = sum(1 for r in rows if r[1] is not None and r[2] is not None and r[2] <= r[1])
        print('\n可比帧 %d ; |A-C| ≤ |A-B| 的 = %d' % (len(rows), eq))
        print('最大 |A-C| = %s ; 最大 |A-B| = %s'
              % (max((r[2] for r in rows if r[2] is not None), default=None),
                 max((r[1] for r in rows if r[1] is not None), default=None)))
    if x.out:
        import io
        with io.open(x.out, 'w', encoding='utf-8') as f:
            f.write('%-24s %10s %10s  %s\n' % ('frame', 'AB_jitter', 'AC', 'verdict'))
            for fn, ab, ac, tag in rows:
                f.write('%-24s %10s %10s  %s\n' % (fn, ab, ac, tag))
        print('→ %s' % x.out)
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
