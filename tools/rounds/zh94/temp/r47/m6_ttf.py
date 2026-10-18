# -*- coding: utf-8 -*-
r"""m6_ttf.py — round47 ⑥: 用 方正像素16.ttf 模板判定单字节记录码的字形**真实落点**。

模板口径与 gen_font16.py 一致: truetype(16), draw at (8,8), 取 canvas[8:24, 8:24] = 16x16 em 窗。
对每条记录: 在矩形附近扫 (dx,dy) ∈ [-6..6]², 找**逐像素 0 误差**的落点。
"""
import io
import os
import sys
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, default_rects   # noqa: E402
import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402
from PIL import Image, ImageDraw, ImageFont                              # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def show(g, tag):
    print('   %s' % tag)
    for y in range(16):
        print('     %2d |%s|' % (y, ''.join('#' if g[y, x] else '.' for x in range(16))))


for tag, ver in (('GR_ZH93', 'GR_ZH93'), ('GR_ZH94', 'GR_ZH94')):
    A = load(ver)
    dflt = default_rects(A['faces'])
    a = A['eng']
    print('=' * 78)
    print('%s: 单字节记录码的字形落点 (TTF 模板逐像素扫描)' % tag)
    h = collections.Counter()
    rows = []
    for code in range(0xAF, 0xFF):
        if code not in dflt:
            continue
        ch = None
        cs = tcslib.Charset()
        for c, b in cs.enc_single.items():
            if b == code:
                ch = c
                break
        if ch is None:
            continue
        tpl = render16(ch)
        u0, v0, u1, v1 = dflt[code]
        best = None
        for dy in range(-6, 7):
            for dx in range(-6, 7):
                x0, y0 = u0 + dx, v0 + dy
                if x0 < 0 or y0 < 0 or x0 + 16 > W or y0 + 16 > H:
                    continue
                cell = a[y0:y0 + 16, x0:x0 + 16]
                err = int((cell != tpl).sum())
                if best is None or err < best[0]:
                    best = (err, dx, dy)
        h[(best[1], best[2], best[0])] += 1
        rows.append((code, ch, u0, v0, best))
    for k, v in sorted(h.items()):
        print('   dx=%+d dy=%+d err=%d  → %d 条' % (k[0], k[1], k[2], v))
    print('   --- 明细 (code ch u0 v0 dx dy err) ---')
    for code, ch, u0, v0, best in rows:
        print('     0x%02X %s u=%4d v=%3d  dx=%+d dy=%+d err=%d%s'
              % (code, ch, u0, v0, best[1], best[2], best[0],
                 '   ★0误差' if best[0] == 0 else ''))
    if tag == 'GR_ZH93':
        print()
        print('   --- 中(0xD6) TTF 模板 ---')
        show(render16('中'), 'TTF 中 (16x16 em 窗)')
        u0, v0, _, _ = dflt[0xD6]
        show(a[v0:v0 + 16, u0:u0 + 16], 'atlas 中 在矩形 (u0,v0)')
        show(a[v0 + 2:v0 + 18, u0:u0 + 16], 'atlas 中 在矩形+(0,2)')
