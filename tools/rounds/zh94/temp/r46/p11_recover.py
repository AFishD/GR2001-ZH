# -*- coding: utf-8 -*-
r"""p11_recover.py — 那 6 个"底部单字节码"的字形能不能从 ZH93 捞回来? 与 TTF 逐像素比对。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import dump_font                                       # noqa: E402
import repack_font                                     # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
CODES = [0x92, 0x9D, 0x9E, 0x9F, 0xA0, 0xFF]
NAME = {0x92: '若', 0x9D: '纤', 0x9E: '终', 0x9F: '脆', 0xA0: '膛', 0xFF: '著'}
fnt = ImageFont.truetype(FZ16, 16)


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def flat_img(A):
    stride = A.w // 2
    n = min(len(A.cont) // stride, A.h)
    a = np.frombuffer(bytes(A.cont[:n * stride]), dtype=np.uint8).reshape(n, stride)
    img = np.zeros((A.h, A.w), dtype=bool)
    img[:n, 0::2] = (a & 0x0F) == 0
    img[:n, 1::2] = (a >> 4) == 0
    return img


def show(g):
    return ['|' + ''.join('#' if v else '.' for v in row) + '|' for row in g]


A93 = repack_font.Atlas(*[dump_font.load_font(
    os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))['atlas'][k]
    for k in ('pak', 'px_off', 'px_size', 'w', 'h', 'psm')])
f94 = dump_font.load_font(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso'))
recs = [x for x in f94['faces'] if x[0] == 'default'][0][2]
F93 = flat_img(A93)

for code in CODES:
    r = recs[code - 0x20]
    u0, v0 = r[2], r[3]
    cand = F93[v0:v0 + 16, u0:u0 + 16]
    tpl = render16(NAME[code])
    # 允许 ±2 像素平移比对 (历史写入有 4/2 偏置)
    best = None
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            t = np.roll(np.roll(tpl, dy, 0), dx, 1)
            inter = int((cand & t).sum())
            union = int((cand | t).sum()) or 1
            iou = inter / union
            if best is None or iou > best[0]:
                best = (iou, dx, dy, inter)
    print('=' * 78)
    print('0x%02X %s  rect=(%d,%d,%d,%d)  ZH93 flat 墨=%d  TTF 墨=%d  最佳 IoU=%.3f (dx=%d dy=%d)'
          % (code, NAME[code], r[2], r[3], r[4], r[5], int(cand.sum()), int(tpl.sum()),
             best[0], best[1], best[2]))
    for i in range(16):
        print('   %s  %s' % (show(cand)[i], show(tpl)[i]))
