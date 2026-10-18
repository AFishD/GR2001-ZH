# -*- coding: utf-8 -*-
r"""cap_diff.py — 两轮同名帧逐像素对比 (round48 实机 A/B 第 1 步)。

用法:
  python cap_diff.py <dirA> <dirB> [--out ab_diff.json] [--tag 名字]

输出: 每帧差异像素数 / 包围盒; 汇总"完全相同 / 有差异"; 差异 (h,w) 直方图;
      并把差异像素的 y 行分布打出来 (用来判断"差异只有字形底部一行")。
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))


def frames(d):
    return sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))


def rgb(p):
    return np.asarray(Image.open(p).convert('RGB'))


def main():
    a = sys.argv[1:]
    da, db = a[0], a[1]
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'ab_diff.json')
    tag = a[a.index('--tag') + 1] if '--tag' in a else 'ab'
    fa, fb = frames(da), frames(db)
    common = sorted(set(fa) & set(fb))
    print('A=%s (%d 帧)  B=%s (%d 帧)  同名帧 %d'
          % (os.path.basename(da.rstrip('\\/')), len(fa),
             os.path.basename(db.rstrip('\\/')), len(fb), len(common)))
    print('仅 A 有 %d 帧; 仅 B 有 %d 帧' % (len(set(fa) - set(fb)), len(set(fb) - set(fa))))
    recs, same = [], 0
    rowhist = {}
    for name in common:
        ia, ib = rgb(os.path.join(da, name)), rgb(os.path.join(db, name))
        if ia.shape != ib.shape:
            recs.append(dict(frame=name, shape=[list(ia.shape), list(ib.shape)]))
            print('  !! %s 尺寸不同' % name)
            continue
        d = np.any(ia != ib, axis=2)
        n = int(d.sum())
        if n == 0:
            same += 1
            continue
        ys, xs = np.where(d)
        for y in np.unique(ys):
            rowhist[int(y)] = rowhist.get(int(y), 0) + int((ys == y).sum())
        recs.append(dict(frame=name, n=n, x0=int(xs.min()), x1=int(xs.max()),
                         y0=int(ys.min()), y1=int(ys.max()),
                         w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1),
                         ys=sorted(set(int(y) for y in ys)),
                         px=[[int(y), int(x)] for y, x in zip(ys[:400], xs[:400])]))
    print('')
    print('逐像素完全相同 %d/%d 帧; 有差异 %d 帧' % (same, len(common), len(recs)))
    if recs:
        hw = {}
        for r in recs:
            if 'h' in r:
                hw[(r['h'], r['w'])] = hw.get((r['h'], r['w']), 0) + 1
        print('差异包围盒 (h,w) → 帧数: %s' % sorted(hw.items()))
        print('差异像素数 min/max/中位: %d / %d / %d'
              % (min(r['n'] for r in recs), max(r['n'] for r in recs),
                 int(np.median([r['n'] for r in recs]))))
        print('差异像素的 y 行分布 (行 → 像素数):')
        for y in sorted(rowhist):
            print('   y=%-4d %d' % (y, rowhist[y]))
        print('')
        print('前 30 个有差异帧:')
        for r in recs[:30]:
            if 'n' in r:
                print('  %s px=%3d bbox x=%d..%d y=%d..%d (%dx%d) 行=%s'
                      % (r['frame'], r['n'], r['x0'], r['x1'], r['y0'], r['y1'],
                         r['w'], r['h'], r['ys']))
        print('  ...(共 %d 帧有差异)' % len(recs))
    doc = dict(A=os.path.abspath(da), B=os.path.abspath(db), tag=tag,
               frames_common=len(common), frames_same=same, frames_diff=len(recs),
               rowhist=rowhist, detail=recs)
    io.open(out, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False) + '\n')
    print('→ %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
