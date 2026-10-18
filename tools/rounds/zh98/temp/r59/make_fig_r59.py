# -*- coding: utf-8 -*-
r"""round59: 出一张图解 (给报告用) —— 旧位置 (贴图右缘 x=1008) / 新位置 (搬字带 y=213) 对照。

产物: work/builds/GR_ZH109/fig_edge_fix.png
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
from patch_zh109_edge_fix import load                                    # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'fig_edge_fix.png')
F = 'C:/Windows/Fonts/msyh.ttc'
RED, GREEN, BLUE, GREY = (220, 30, 30), (0, 160, 60), (0, 90, 220), (150, 150, 150)


def gray(M):
    return np.where(M['ink'], 0, 255).astype(np.uint8)


def crop(img, x0, y0, x1, y1, scale, boxes=()):
    blk = Image.fromarray(img[y0:y1, x0:x1]).convert('RGB')
    blk = blk.resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
    d = ImageDraw.Draw(blk)
    for (bx0, by0, bx1, by1, col, wd) in boxes:
        d.rectangle([(bx0 - x0) * scale, (by0 - y0) * scale,
                     (bx1 - x0) * scale - 1, (by1 - y0) * scale - 1], outline=col, width=wd)
    return blk


def main():
    P = os.path.join(REPO, 'work', 'builds')
    g98 = gray(load(os.path.join(P, 'GR_ZH98', 'GR_ZH98.iso')))
    g108 = gray(load(os.path.join(P, 'GR_ZH108', 'GR_ZH108.iso')))
    g109 = gray(load(os.path.join(P, 'GR_ZH109', 'GR_ZH109.iso')))
    f1 = ImageFont.truetype(F, 21)
    f2 = ImageFont.truetype(F, 15)
    f3 = ImageFont.truetype(F, 13)

    X0, Y0 = 16, 16
    # ── 第 1 行: 4 个字形 (8 倍 + 下方 3 行字) ──
    GS, TILE_W, CAPH = 8, 250, 76
    tiles = [('搬字前 (GR_ZH98)', '(288,354,304,370)', g98, (288, 354, 304, 370), '个 0xEE'),
             ('现役 (GR_ZH108)', '(1008,195,1024,211) 贴图右缘', g108, (1008, 195, 1024, 211),
              '个 0xEE'),
             ('修复后 (GR_ZH109)', '(352,213,368,229)', g109, (352, 213, 368, 229), '个 0xEE'),
             ('修复后 (GR_ZH109)', '(320,213,336,229)', g109, (320, 213, 336, 229), '这 0xED')]
    R1Y = Y0 + 34
    row1_h = 16 * GS + CAPH
    # ── 第 2/3 行: 图集带 (左右各一块) ──
    bA = crop(g108, 944, 190, 1024, 234, 6, [(992, 195, 1008, 211, RED, 3)])
    bB = crop(g109, 944, 190, 1024, 234, 6, [(992, 195, 1008, 211, GREY, 3)])
    bC = crop(g108, 304, 205, 512, 235, 6, [(320, 213, 368, 229, GREY, 3)])
    bD = crop(g109, 304, 205, 512, 235, 6, [(320, 213, 336, 229, GREEN, 3),
                                            (352, 213, 368, 229, GREEN, 3),
                                            (480, 213, 490, 229, BLUE, 3)])
    colw = max(bA.width, bC.width)
    W = max(X0 + 4 * TILE_W, X0 + colw + X0 + bD.width + X0)
    R2Y = R1Y + row1_h + 46
    R3Y = R2Y + 22 + bA.height + 52
    im = Image.new('RGB', (W, R3Y + 22 + bC.height + 24), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.text((X0, Y0), 'GR_ZH109 贴图右缘修复: 单字节码 0xEE「个」从贴图右缘 (1008,195) 搬回 (352,213)'
                     '    [图 = engine 口径图集, 黑 = 墨]', fill=(0, 0, 0), font=f1)
    for i, (cap, rc, img, (x0, y0, x1, y1), ch) in enumerate(tiles):
        x = X0 + i * TILE_W
        im.paste(Image.fromarray(img[y0:y1, x0:x1]).convert('RGB')
                 .resize((16 * GS, 16 * GS), Image.NEAREST), (x, R1Y))
        d.rectangle([x - 1, R1Y - 1, x + 16 * GS, R1Y + 16 * GS], outline=(120, 120, 120))
        d.text((x, R1Y + 16 * GS + 4), '%s   %s' % (ch, cap), fill=(0, 0, 0), font=f2)
        d.text((x, R1Y + 16 * GS + 26), rc, fill=(70, 70, 70), font=f3)
        d.text((x, R1Y + 16 * GS + 46), '墨 54 px' if ch.startswith('这') else '墨 26 px',
               fill=(70, 70, 70), font=f3)
    d.text((X0, R2Y), '① GR_ZH108 现役: 图集右缘 (x=944..1024 / y=190..234); 红框 = 「个」所在 (1008,195)',
           fill=(0, 0, 0), font=f3)
    im.paste(bA, (X0, R2Y + 22))
    d.text((X0 + colw + X0, R2Y), '② GR_ZH109: 同一片区域 —— 红框处已清空 (「个」搬走了)',
           fill=(0, 0, 0), font=f3)
    im.paste(bB, (X0 + colw + X0, R2Y + 22))
    d.text((X0, R3Y), '③ GR_ZH108 现役: 搬字带 (x=304..512 / y=205..235) —— 「个」不在这里',
           fill=(0, 0, 0), font=f3)
    im.paste(bC, (X0, R3Y + 22))
    d.text((X0 + colw + X0, R3Y), '④ GR_ZH109: 绿框 = 这(320,213) / 个(352,213);  蓝框 = 17 条空记录共用的空矩形(480,213)',
           fill=(0, 0, 0), font=f3)
    im.paste(bD, (X0 + colw + X0, R3Y + 22))
    im.save(OUT)
    print('[fig] %s  %dx%d' % (OUT, im.width, im.height))
    return 0


if __name__ == '__main__':
    sys.exit(main())
