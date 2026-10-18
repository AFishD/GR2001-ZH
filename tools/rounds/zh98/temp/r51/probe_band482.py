# -*- coding: utf-8 -*-
"""r51 探针④: 单字节码 0x80..0x9C (记录在 y=482 带) 的盘上像素 vs 模板 到底差在哪。只读。"""
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
cs = tcslib.Charset()

for c in (0x82, 0x8C, 0x80):
    ch = cs.codes.get(c, '?')
    r = recs[c - 0x20]
    sub = ink[r[3]:r[5], r[2]:r[4]]
    t = tpl(ch)
    print('==== code %02X %r rec=(%d,%d,%d,%d) 盘墨=%d 模板墨=%d' % (c, ch, r[2], r[3], r[4], r[5],
                                                                 int(sub.sum()), int(t.sum())))
    print('     盘上格                          模板                            异或')
    for y in range(16):
        print('   %s  %s  %s'
              % (''.join('#' if sub[y, x] else '.' for x in range(16)),
                 ''.join('#' if t[y, x] else '.' for x in range(16)),
                 ''.join('X' if (sub[y, x] != t[y, x]) else '.' for x in range(16))))
    # 最佳整数位移
    best = None
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            blk = np.zeros_like(sub)
            for y in range(16):
                for x in range(16):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < 16 and 0 <= xx < 16:
                        blk[y, x] = t[yy, xx]
            d = int((blk ^ sub).sum())
            if best is None or d < best[0]:
                best = (d, dx, dy)
    print('   >> 最佳位移 dx=%d dy=%d 差异=%d (原位差异=%d)' % (best[1], best[2], best[0],
                                                            int((sub ^ t).sum())))

print()
print('=== 该带的记录清单 (v0=482 一族的 code) ===')
codes = sorted(idx + 0x20 for idx, r in enumerate(recs) if r[3] == 482)
print('  v0=482 的码: %s' % ' '.join('%02X' % c for c in codes))
codes2 = sorted(idx + 0x20 for idx, r in enumerate(recs) if r[3] == 452)
print('  v0=452 的码: %02X..%02X (%d 个)' % (codes2[0], codes2[-1], len(codes2)))
print()
print('=== 三个 face 在 0x80 处的记录 ===')
for fi, (n2, _f, rs) in enumerate(faces):
    print('  face %d %-8s code 0x80 rec=%s ; code 0xAF rec=%s ; code 0x20 rec=%s'
          % (fi, n2, rs[0x80 - 0x20], rs[0xAF - 0x20], rs[0]))
