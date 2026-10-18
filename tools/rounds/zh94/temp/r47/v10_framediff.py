# -*- coding: utf-8 -*-
r"""v10_framediff.py — round47 实机验收: 两盘抓帧逐像素对比。

补丁只改了图集里 76 个 texel (全在 y=353, 20 个记录格)。⇒
  · 屏幕上**只应该**在这 20 个字 (单字节码 0xC2..0xDA) 的渲染处出现差异;
  · 其余整帧必须 0 差异。
本脚本: 逐帧统计差异像素 + 包围盒 + 打印差异区 ASCII (用来认出是哪个字、哪一行)。
"""
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def frames(d):
    return sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))


def gray(p):
    return np.asarray(Image.open(p).convert('L'))


def ascii_win(a, x0, x1, y0, y1):
    return ['%4d |%s|' % (y, ''.join('#' if a[y, x] < 128 else '.' for x in range(x0, x1)))
            for y in range(y0, y1)]


def main(da, db, out=None):
    fa, fb = frames(da), frames(db)
    common = sorted(set(fa) & set(fb))
    print('A=%s (%d 帧)  B=%s (%d 帧)  同名帧 %d'
          % (os.path.basename(da.rstrip('\\/')), len(fa),
             os.path.basename(db.rstrip('\\/')), len(fb), len(common)))
    nz = 0
    tot = 0
    report = []
    for name in common:
        a = gray(os.path.join(da, name))
        b = gray(os.path.join(db, name))
        if a.shape != b.shape:
            print('  !! %s 尺寸不同 %s %s' % (name, a.shape, b.shape))
            continue
        d = (a != b)
        n = int(d.sum())
        tot += n
        if n:
            nz += 1
            ys, xs = np.where(d)
            y0, y1, x0, x1 = int(ys.min()), int(ys.max()), int(xs.min()), int(xs.max())
            print()
            print('=' * 78)
            print('帧 %s: 差异 %d 像素; 包围盒 x=%d..%d y=%d..%d'
                  % (name, n, x0, x1, y0, y1))
            print('  差异坐标: %s' % list(zip(ys.tolist(), xs.tolist()))[:40])
            X0, X1 = max(0, x0 - 20), min(a.shape[1], x1 + 21)
            Y0, Y1 = max(0, y0 - 12), min(a.shape[0], y1 + 13)
            for tag, img in (('A', a), ('B', b)):
                print('  --- %s ---' % tag)
                for ln in ascii_win(img, X0, X1, Y0, Y1):
                    print('  ' + ln)
            report.append(dict(frame=name, n=n, box=[x0, y0, x1, y1],
                               px=[[int(y), int(x)] for y, x in zip(*np.where(d))]))
    print()
    print('=' * 78)
    print('★ 汇总: %d/%d 帧有差异 (共 %d 像素); 其余 %d 帧**逐像素完全相同**'
          % (nz, len(common), tot, len(common) - nz))
    if out:
        import json
        import io
        io.open(out, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(dict(frames=len(common), diff_frames=nz, diff_pixels=tot, detail=report),
                       ensure_ascii=False, indent=1) + '\n')
        print('  → %s' % out)


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[a.index('--out') + 1] if '--out' in a else None)
