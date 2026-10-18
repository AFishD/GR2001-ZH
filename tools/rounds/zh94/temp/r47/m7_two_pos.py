# -*- coding: utf-8 -*-
r"""m7_two_pos.py — round47 ⑦: 单字节码的字形到底存在哪? 两个候选位置都查。

候选 A = 记录矩形 (u0, v0)                       （round45 报告口径: 记录矩形就是采样窗）
候选 B = ((u0+576) mod 1024, v0+1)               （REPORT_font_ext_zh93 §2.2(b) 实机探针口径）
"""
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


cs = tcslib.Charset()
rev = dict((b, c) for c, b in cs.enc_single.items())
for ver in ('GR_ZH93', 'GR_ZH94'):
    A = load(ver)
    a = A['eng']
    dflt = default_rects(A['faces'])
    print('=' * 78)
    print('%s: 候选 A=(u0,v0) / B=((u0+576)%%1024, v0+1) 的模板误差' % ver)
    cnt = collections.Counter()
    for code in range(0xAF, 0xFF):
        ch = rev.get(code)
        if ch is None or code not in dflt:
            continue
        tpl = render16(ch)
        u0, v0, u1, v1 = dflt[code]
        ea = int((a[v0:v0 + 16, u0:u0 + 16] != tpl).sum())
        bx, by = (u0 + 576) % 1024, v0 + 1
        eb = int((a[by:by + 16, bx:bx + 16] != tpl).sum())
        cnt[(ea, eb)] += 1
        flag = ''
        if ea == 0 and eb == 0:
            flag = ' (两处都有)'
        elif ea == 0:
            flag = ' ← A 命中'
        elif eb == 0:
            flag = ' ← B 命中'
        print('   0x%02X %s 记录(%4d,%3d)  A_err=%2d  B=(%4d,%3d) B_err=%2d%s'
              % (code, ch, u0, v0, ea, bx, by, eb, flag))
    print('  ★ (A_err, B_err) 分布: %s' % cnt.most_common(10))
