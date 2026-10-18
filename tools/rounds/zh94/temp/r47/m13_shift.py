# -*- coding: utf-8 -*-
r"""m13_shift.py — round47 ⑬: "别处"那批 (行 24 / EN 带 的单字节码) 到底是不是**整格偏 1 行**。

调色板: 模板 vs 现格在 dy ∈ {-2,-1,0,1,2}, dx ∈ {-1,0,1} 下的误差。
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, default_rects  # noqa: E402
import numpy as np                                                      # noqa: E402
import tcslib                                                           # noqa: E402
from PIL import Image, ImageDraw, ImageFont                             # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


A = load('GR_ZH93')
a = A['eng']
dflt = default_rects(A['faces'])
cs = tcslib.Charset()
rev = dict((b, c) for c, b in cs.enc_single.items())

groups = {'行24 (v0=434)': [], 'EN带 (v0=482)': [], '行18 (v0=338)': [], '行11 (v0=178)': [],
          '行19 (v0=354)': []}
for code, (u0, v0, u1, v1) in sorted(dflt.items()):
    if (u1 - u0, v1 - v0) != (16, 16):
        continue
    ch = rev.get(code)
    if not ch:
        continue
    key = {434: '行24 (v0=434)', 482: 'EN带 (v0=482)', 338: '行18 (v0=338)',
           178: '行11 (v0=178)', 354: '行19 (v0=354)'}.get(v0)
    if key is None:
        continue
    tpl = render16(ch)
    best = None
    table = {}
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-1, 0, 1):
            x0, y0 = u0 + dx, v0 + dy
            if x0 < 0 or y0 < 0 or x0 + 16 > W or y0 + 16 > H:
                continue
            e = int((a[y0:y0 + 16, x0:x0 + 16] != tpl).sum())
            table[(dx, dy)] = e
            if best is None or e < best[0]:
                best = (e, dx, dy)
    flat = table[(0, 0)]
    groups[key].append((code, ch, flat, best))

print('=' * 78)
print('各组的 (dx,dy) 最优落点分布 —— 判断字形是不是"整格偏 1 行"')
for k, v in groups.items():
    c = collections.Counter((b[3][1], b[3][2], b[3][0]) for b in v)
    print('  %-14s %d 条: 最优 (dx,dy,err) 分布 %s' % (k, len(v), c.most_common(6)))
    print('     居中(err@0,0)=%s' % collections.Counter(b[2] for b in v).most_common(6))
    for code, ch, flat, best in v:
        if best[1] or best[2]:
            print('       0x%02X %s  (0,0)err=%d  最优 dx=%+d dy=%+d err=%d'
                  % (code, ch, flat, best[1], best[2], best[0]))
