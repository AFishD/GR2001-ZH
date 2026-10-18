# -*- coding: utf-8 -*-
r"""ab3_montage.py — 把若干帧按网格拼成对照图 (可裁剪 + 最近邻放大 + 帧号标签)。

用法:
  python ab3_montage.py --out <png> --cols 2 [--scale 3] [--box x0,y0,x1,y1]
                       --item <dir> <frame.png> [--label 文本] [--item ...]

label 里可用 \n 换行; 中文标签用 PIL 默认字体画不出来 ⇒ 标签只写 ASCII/帧号。
"""
import os
import sys

from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def parse(argv):
    o = dict(out=None, cols=2, scale=1, box=None, items=[])
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--out':
            o['out'] = argv[i + 1]; i += 2
        elif a == '--cols':
            o['cols'] = int(argv[i + 1]); i += 2
        elif a == '--scale':
            o['scale'] = float(argv[i + 1]); i += 2
        elif a == '--box':
            o['box'] = [int(v) for v in argv[i + 1].split(',')]; i += 2
        elif a == '--item':
            d, f = argv[i + 1], argv[i + 2]
            lab = f
            i += 3
            if i < len(argv) and argv[i] == '--label':
                lab = argv[i + 1]; i += 2
            o['items'].append((d, f, lab))
        else:
            raise SystemExit('bad arg %r' % a)
    return o


def main():
    o = parse(sys.argv[1:])
    tiles = []
    for (d, f, lab) in o['items']:
        im = Image.open(os.path.join(d, f)).convert('RGB')
        if o['box']:
            im = im.crop(tuple(o['box']))
        if o['scale'] != 1:
            im = im.resize((max(1, int(im.width * o['scale'])),
                            max(1, int(im.height * o['scale']))), Image.NEAREST)
        tiles.append((im, lab))
    cols = o['cols']
    rows = (len(tiles) + cols - 1) // cols
    w = max(t[0].width for t in tiles)
    h = max(t[0].height for t in tiles) + 12
    out = Image.new('RGB', (cols * w, rows * h), (32, 32, 32))
    dr = ImageDraw.Draw(out)
    for k, (im, lab) in enumerate(tiles):
        r, c = divmod(k, cols)
        out.paste(im, (c * w, r * h + 12))
        dr.text((c * w + 3, r * h + 1), lab[:60], fill=(255, 255, 0))
    out.save(o['out'])
    print('→ %s  %dx%d  tiles=%d' % (o['out'], out.width, out.height, len(tiles)))


if __name__ == '__main__':
    main()
