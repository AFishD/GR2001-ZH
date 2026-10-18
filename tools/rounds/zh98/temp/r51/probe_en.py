# -*- coding: utf-8 -*-
"""r51 探针②: ASCII 8x16 记录 vs 方正像素16 16px 模板 的对齐关系。只读。"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib
import dump_font
from PIL import Image, ImageDraw, ImageFont

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
font = dump_font.load_font(ISO)
faces = font['faces']
atlas = font['atlas']
gray = dump_font.atlas_gray(atlas, view='engine')
ink = (np.frombuffer(gray, np.uint8).reshape(atlas['h'], atlas['w']) == 0)

fnt = ImageFont.truetype(TTF, 16)


def tpl(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


nm, fld, recs = faces[tcslib.FONT_FACE_DEFAULT]

print('=== ASCII: 模板 bbox vs 记录矩形 ===')
for c in (0x21, 0x28, 0x49, 0x57, 0x6D, 0x7A, 0x3F, 0x2E, 0x6A):
    ch = chr(c)
    t = tpl(ch)
    ys, xs = np.where(t)
    r = recs[c - 0x20]
    sub = ink[r[3]:r[5], r[2]:r[4]]
    ys2, xs2 = np.where(sub)
    print('%r rec=(%d,%d,%d,%d) 盘墨=%d bbox(x%d..%d,y%d..%d) | 模板墨=%d bbox(x%d..%d,y%d..%d)'
          % (ch, r[2], r[3], r[4], r[5], int(sub.sum()),
             xs2.min() if len(xs2) else -1, xs2.max() if len(xs2) else -1,
             ys2.min() if len(ys2) else -1, ys2.max() if len(ys2) else -1,
             int(t.sum()), xs.min() if len(xs) else -1, xs.max() if len(xs) else -1,
             ys.min() if len(ys) else -1, ys.max() if len(ys) else -1))
    # 试: 模板左 8 列
    if sub.shape == (16, 8):
        for dx in range(0, 9):
            blk = t[:, dx:dx + 8]
            if blk.shape == (16, 8):
                d = int((blk ^ sub).sum())
                if d <= 3:
                    print('     dx=%d 差异像素=%d  (模板列 %d..%d)' % (dx, d, dx, dx + 7))
    print('     模板整行墨列: %s' % ''.join('#' if t[:, x].any() else '.' for x in range(16)))
    print('     盘上整行墨列: %s' % ''.join('#' if sub[:, x].any() else '.' for x in range(8)))
