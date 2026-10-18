# -*- coding: utf-8 -*-
r"""p23_sheet.py — 把一个转储目录的帧拼成缩略图总览 (看清这一跑到底经过了哪些画面)。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image                                           # noqa: E402


def main():
    d = sys.argv[1]
    out = sys.argv[2]
    step = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    cols = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    fs = sorted(f for f in os.listdir(d) if f.startswith('snap_f') and f.endswith('.png'))[::step]
    if not fs:
        print('没有帧'); return
    im0 = Image.open(os.path.join(d, fs[0]))
    tw = 240
    th = max(1, int(im0.size[1] * tw / im0.size[0]))
    rows = (len(fs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * tw, rows * (th + 12)), (20, 20, 20))
    from PIL import ImageDraw
    dr = ImageDraw.Draw(sheet)
    for i, fn in enumerate(fs):
        im = Image.open(os.path.join(d, fn)).convert('RGB').resize((tw, th))
        x, y = (i % cols) * tw, (i // cols) * (th + 12)
        sheet.paste(im, (x, y + 12))
        dr.text((x + 3, y + 1), fn.replace('snap_f', '').replace('.png', ''), fill=(255, 220, 80))
    sheet.save(out, optimize=True)
    print('-> %s %s (%d 帧)' % (out, sheet.size, len(fs)))


if __name__ == '__main__':
    main()
