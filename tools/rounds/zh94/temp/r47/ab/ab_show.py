# -*- coding: utf-8 -*-
r"""ab_show.py — round47 实机 A/B: 生成"同帧放大对照图" (修前 | 修后 | 差分)。

用法:
  python ab_show.py --before <dirA> --after <dirB> --frame snap_f00028000.png
                    --out <png> [--box x0,y0,x1,y1 | --around x,y,w,h] [--zoom 8]
                    [--ascii] [--title 文本]

· 裁剪同一帧、同一区域, 最近邻放大;
· 三栏: 修前(GR_ZH94) / 修后(GR_ZH96_fix) / 差分(白=不同);
· --ascii 时同时打印该区域的 ASCII (字形=亮 '#') 与差异像素坐标。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def parse(argv):
    o = dict(box=None, zoom=8, ascii=False, title=None)
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.lstrip('-') in ('before', 'after', 'frame', 'out', 'box', 'zoom', 'around', 'title'):
            k = a.lstrip('-')
            if k == 'ascii':
                o['ascii'] = True; i += 1; continue
            v = argv[i + 1]
            if k == 'zoom':
                o[k] = int(v)
            elif k == 'box':
                o[k] = [int(x) for x in v.split(',')]
            elif k == 'around':
                x, y, w, h = [int(x) for x in v.split(',')]
                o['box'] = [x - w // 2, y - h // 2, x + w // 2, y + h // 2]
            else:
                o[k] = v
            i += 2
        elif a == '--ascii':
            o['ascii'] = True; i += 1
        else:
            raise SystemExit('bad arg %r' % a)
    return o


def main():
    o = parse(sys.argv[1:])
    pa = os.path.join(o['before'], o['frame'])
    pb = os.path.join(o['after'], o['frame'])
    A = np.asarray(Image.open(pa).convert('RGB'))
    B = np.asarray(Image.open(pb).convert('RGB'))
    if A.shape != B.shape:
        raise SystemExit('尺寸不同 %s %s' % (A.shape, B.shape))
    D = np.any(A != B, axis=2)
    x0, y0, x1, y1 = o['box']
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(A.shape[1], x1), min(A.shape[0], y1)

    def tile(img, lab):
        c = Image.fromarray(img[y0:y1, x0:x1])
        c = c.resize((c.width * o['zoom'], c.height * o['zoom']), Image.NEAREST)
        t = Image.new('RGB', (c.width, c.height + 16), (24, 24, 24))
        t.paste(c, (0, 16))
        ImageDraw.Draw(t).text((3, 3), lab, fill=(255, 255, 0))
        return t

    dm = np.zeros_like(A)
    dm[D] = (255, 255, 255)
    tiles = [tile(A, 'BEFORE GR_ZH94  %s' % o['frame']),
             tile(B, 'AFTER  GR_ZH96_fix'),
             tile(np.where(D[:, :, None], np.array([255, 60, 60], np.uint8), np.zeros_like(A)),
                  'DIFF %d px' % int(D.sum()))]
    W = sum(t.width for t in tiles) + 12
    H = max(t.height for t in tiles) + 4
    out = Image.new('RGB', (W, H), (24, 24, 24))
    x = 0
    for t in tiles:
        out.paste(t, (x, 2))
        x += t.width + 6
    out.save(o['out'])
    print('→ %s  %dx%d  box=(%d,%d)-(%d,%d) zoom=%d  差异 %d px'
          % (o['out'], out.width, out.height, x0, y0, x1, y1, o['zoom'], int(D.sum())))

    if o['ascii']:
        ys, xs = np.where(D)
        if len(ys):
            print('  差异像素坐标(整帧): %s' % list(zip(ys.tolist(), xs.tolist()))[:60])
        ga = np.asarray(Image.open(pa).convert('L'))
        gb = np.asarray(Image.open(pb).convert('L'))
        print('  --- 修前 ASCII ---')
        for y in range(y0, y1):
            print('  %4d |%s|' % (y, ''.join('#' if ga[y, x] >= 128 else '.' for x in range(x0, x1))))
        print('  --- 修后 ASCII ---')
        for y in range(y0, y1):
            print('  %4d |%s|' % (y, ''.join('#' if gb[y, x] >= 128 else '.' for x in range(x0, x1))))


if __name__ == '__main__':
    main()
