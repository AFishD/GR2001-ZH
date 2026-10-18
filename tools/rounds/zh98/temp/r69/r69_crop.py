# -*- coding: utf-8 -*-
r"""r69_crop.py — 从多张图裁同一矩形, 3 倍放大后纵向拼接 (对照用)。

用法: python r69_crop.py <out.png> <x0> <y0> <x1> <y1> <img1> <img2> [...]
"""
import os
import sys

from PIL import Image, ImageDraw


def main():
    out = sys.argv[1]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[2:6])
    imgs = sys.argv[6:]
    scale = 3
    tiles = []
    for p in imgs:
        im = Image.open(p).convert('RGB').crop((x0, y0, x1, y1))
        im = im.resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
        lab = Image.new('RGB', (im.width, im.height + 22), (0, 0, 0))
        lab.paste(im, (0, 22))
        d = ImageDraw.Draw(lab)
        d.text((4, 5), os.path.basename(p)[:60], fill=(255, 255, 0))
        tiles.append(lab)
    w = max(t.width for t in tiles)
    h = sum(t.height for t in tiles) + 6 * (len(tiles) - 1)
    canvas = Image.new('RGB', (w, h), (40, 40, 40))
    y = 0
    for t in tiles:
        canvas.paste(t, (0, y))
        y += t.height + 6
    canvas.save(out)
    print('-> %s  (%dx%d, %d 张, 裁 (%d,%d)-(%d,%d) x%d)'
          % (out, canvas.width, canvas.height, len(tiles), x0, y0, x1, y1, scale))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
