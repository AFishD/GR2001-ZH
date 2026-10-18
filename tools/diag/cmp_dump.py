# -*- coding: utf-8 -*-
r"""cmp_dump.py — 逐帧比对两个 gsrunner 转储目录 (实机 A/B 回归用)。

用法:
  python tools/diag/cmp_dump.py <转储A> <转储B> [--tol N] [--show K] [--out <对照图前缀>]

口径:
  · 按文件名配对 (snap_f00012345.png); 只在两边都有的文件名上比;
  · 逐像素比对 (原尺寸, 不缩放); 差异像素数 <= --tol 视为同一帧 (默认 0 = 严格逐像素);
  · 输出: 相同帧数 / 不同帧数 / 只在一边有的帧; 并打印前 --show 个不同帧的文件名与差异像素数;
  · --out 给了就为前若干不同帧出「A|B 并排」对照 PNG (方便肉眼定位)。
"""
import argparse
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def imread_u(p):
    import cv2
    import numpy as np
    return cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_u(p, img):
    import cv2
    import numpy as np
    ok, buf = cv2.imencode(os.path.splitext(p)[1], img)
    if ok:
        buf.tofile(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a')
    ap.add_argument('b')
    ap.add_argument('--tol', type=int, default=0, help='允许的差异像素数 (默认 0)')
    ap.add_argument('--show', type=int, default=20, help='打印前几个不同帧')
    ap.add_argument('--out', default=None, help='不同帧的 A|B 并排对照图前缀')
    ap.add_argument('--pattern', default='snap_f', help='帧文件名前缀')
    a = ap.parse_args()
    import numpy as np

    fa = sorted(f for f in os.listdir(a.a) if f.startswith(a.pattern) and f.endswith('.png'))
    fb = sorted(f for f in os.listdir(a.b) if f.startswith(a.pattern) and f.endswith('.png'))
    sa, sb = set(fa), set(fb)
    print('[cmp] A=%s (%d 帧)' % (a.a, len(fa)))
    print('[cmp] B=%s (%d 帧)' % (a.b, len(fb)))
    only_a, only_b = sorted(sa - sb), sorted(sb - sa)
    if only_a:
        print('[cmp] 只在 A 有: %d 个 %s%s' % (len(only_a), only_a[:4], ' …' if len(only_a) > 4 else ''))
    if only_b:
        print('[cmp] 只在 B 有: %d 个 %s%s' % (len(only_b), only_b[:4], ' …' if len(only_b) > 4 else ''))
    common = sorted(sa & sb)
    same = 0
    diff = []
    shape_bad = []
    for i, fn in enumerate(common):
        ia = imread_u(os.path.join(a.a, fn))
        ib = imread_u(os.path.join(a.b, fn))
        if ia is None or ib is None:
            shape_bad.append((fn, '读取失败'))
            continue
        if ia.shape != ib.shape:
            shape_bad.append((fn, '%s vs %s' % (ia.shape, ib.shape)))
            continue
        d = int((ia != ib).any(axis=2).sum()) if ia.ndim == 3 else int((ia != ib).sum())
        if d <= a.tol:
            same += 1
        else:
            diff.append((fn, d))
            if a.out and len(diff) <= 8:
                h = np.full((ia.shape[0], 6, 3), 255, np.uint8)
                viz = np.hstack([ia, h, ib])
                import cv2
                cv2.putText(viz, 'A', (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(viz, 'B', (ia.shape[1] + 12, 22), cv2.FONT_HERSHEY_SIMPLEX,
                            0.7, (0, 0, 255), 2)
                imwrite_u('%s_%s' % (a.out, fn), viz)
    print('[cmp] 配对帧 %d; **逐像素完全相同 %d**; 不同 %d; 尺寸/读取异常 %d'
          % (len(common), same, len(diff), len(shape_bad)))
    if shape_bad:
        for fn, why in shape_bad[:5]:
            print('       !! %s %s' % (fn, why))
    for fn, d in diff[:a.show]:
        print('       差异 %-24s %d 像素' % (fn, d))
    if len(diff) > a.show:
        print('       … 还有 %d 帧不同' % (len(diff) - a.show))
    if a.out and diff:
        print('[cmp] 对照图 → %s_<帧名>.png (前 8 帧)' % a.out)
    return 0 if (not diff and not shape_bad and not only_a and not only_b) else 1


if __name__ == '__main__':
    sys.exit(main())
