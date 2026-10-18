# -*- coding: utf-8 -*-
r"""ab_diff.py — round47 实机 A/B 第 1 步: 两轮同名帧逐像素对比。

用法:
  python ab_diff.py <dirA> <dirB> [--out <json>] [--log <log>]

输出:
  · 每帧差异像素数 / 包围盒 / 差异像素列表(上限);
  · 汇总: 完全相同的帧数、有差异的帧数、差异像素总数;
  · 差异包围盒的尺寸直方图 (用来判断"差异只有字形底部一条" —— 包围盒应该很矮)。
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
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    da, db = a[0], a[1]
    out = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'ab_diff.json')
    fa, fb = frames(da), frames(db)
    common = sorted(set(fa) & set(fb))
    print('A=%s (%d 帧)  B=%s (%d 帧)  同名帧 %d'
          % (os.path.basename(da.rstrip('\\/')), len(fa),
             os.path.basename(db.rstrip('\\/')), len(fb), len(common)))
    print('仅 A 有: %d 帧; 仅 B 有: %d 帧' % (len(set(fa) - set(fb)), len(set(fb) - set(fa))))

    recs = []
    same = 0
    for name in common:
        ia = rgb(os.path.join(da, name))
        ib = rgb(os.path.join(db, name))
        if ia.shape != ib.shape:
            recs.append(dict(frame=name, shape=[list(ia.shape), list(ib.shape)]))
            print('  !! %s 尺寸不同 %s %s' % (name, ia.shape, ib.shape))
            continue
        d = np.any(ia != ib, axis=2)
        n = int(d.sum())
        if n == 0:
            same += 1
            continue
        ys, xs = np.where(d)
        recs.append(dict(frame=name, n=n,
                         x0=int(xs.min()), x1=int(xs.max()),
                         y0=int(ys.min()), y1=int(ys.max()),
                         w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1),
                         px=[[int(y), int(x)] for y, x in zip(ys[:200], xs[:200])]))
    print()
    print('逐像素完全相同 %d/%d 帧; 有差异 %d 帧'
          % (same, len(common), len(recs)))
    if recs:
        hs = sorted(set((r.get('h'), r.get('w')) for r in recs if 'h' in r))
        print('差异包围盒 (h,w) 取值: %s' % hs[:20])
        print('差异像素数 min/max: %d / %d' % (min(r['n'] for r in recs),
                                              max(r['n'] for r in recs)))
        print()
        print('前 25 个有差异的帧:')
        for r in recs[:25]:
            if 'n' in r:
                print('  %s  px=%3d  bbox x=%d..%d y=%d..%d  (%dx%d)'
                      % (r['frame'], r['n'], r['x0'], r['x1'], r['y0'], r['y1'], r['w'], r['h']))
        print('  ...(共 %d 帧有差异)' % len(recs))

    doc = dict(A=da, B=db, frames_common=len(common), frames_same=same,
               frames_diff=len(recs), detail=recs)
    io.open(out, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False) + '\n')
    print('→ %s' % out)


if __name__ == '__main__':
    main()
