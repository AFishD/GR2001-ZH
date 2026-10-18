# -*- coding: utf-8 -*-
r"""mk_compare.py — 人眼证据: GR_ZH103 vs GR_ZH104 的"被占格 / 空区"对照图。

三条带 (y 取自实际被腾空的网格行 + 新家):
  · y=176..211  : 网格行 11 (178..193) + 新家带 A (195..210)
  · y=336..372  : 网格行 19/20 (338..353 / 354..369) —— 单字节汉字被搬走的行
  · y=390..452  : 网格行 21/22/23/24 (箭头/çñ/行24 的 7 个单字节字)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                          # noqa: E402

BANDS = [(176, 212, '网格行 11 (y=178..193) + 新家带 A (y=195..210)'),
         (336, 372, '网格行 19/20 (y=338..369)'),
         (390, 452, '网格行 21/22/23/24 (y=390..449)')]
S = 2
PAD, LAB = 12, 26


def gray(iso):
    w = D.load_font(iso)
    ad = w['atlas']
    return np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(ad['h'], ad['w'])


def panel(g, title):
    hh = sum(b - a for a, b, _ in BANDS) * S + LAB * len(BANDS) + PAD * 2
    im = Image.new('RGB', (g.shape[1] * S + PAD * 2, hh + 30), (255, 255, 255))
    d = ImageDraw.Draw(im)
    try:
        f1 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
        f2 = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 14)
    except Exception:                                                 # noqa: BLE001
        f1 = f2 = ImageFont.load_default()
    d.text((PAD, 4), title, fill=(0, 0, 0), font=f1)
    y = 30 + PAD
    for (a, b, name) in BANDS:
        d.text((PAD, y), 'y=%d..%d  %s' % (a, b - 1, name), fill=(120, 60, 0), font=f2)
        y += LAB
        blk = Image.fromarray(g[a:b]).convert('RGB')
        blk = blk.resize((g.shape[1] * S, (b - a) * S), Image.NEAREST)
        im.paste(blk, (PAD, y))
        d.rectangle([PAD - 1, y - 1, PAD + g.shape[1] * S, y + (b - a) * S],
                    outline=(200, 200, 200))
        y += (b - a) * S + PAD
    return im


a = panel(gray(os.path.join(REPO, 'work', 'builds', 'GR_ZH103', 'GR_ZH103.iso')),
          'GR_ZH103 (现役): 88 个对偶格被单字节字形占着 + 新家空区是空的')
b = panel(gray(os.path.join(REPO, 'work', 'builds', 'GR_ZH104', 'GR_ZH104.iso')),
          'GR_ZH104 (本补丁): 那些格全空 + 84 条字形搬到 y=195..226 空区')
out = Image.new('RGB', (max(a.width, b.width), a.height + b.height + 8), (255, 255, 255))
out.paste(a, (0, 0))
out.paste(b, (0, a.height + 8))
p = os.path.join(HERE, 'atlas_before_after.png')
out.save(p)
print('[out] %s  (%dx%d)' % (p, out.width, out.height))
