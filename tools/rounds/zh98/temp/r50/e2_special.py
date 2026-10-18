# -*- coding: utf-8 -*-
"""r50 临时: 检查 14 个非汉字对偶码 (含 ± ® 全角标点) 的字形几何 + 与 TTF 模板比对。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402

ISO = os.path.join(REPO, 'work/builds/GR_ZH98/GR_ZH98.iso')
font = dump_font.load_font(ISO)
gray = dump_font.atlas_gray(font['atlas'], view='engine')
W, H = font['atlas']['w'], font['atlas']['h']
ink = (np.frombuffer(gray, np.uint8).reshape(H, W) == 0)
cs = tcslib.Charset()
fnt = ImageFont.truetype(os.path.join(REPO, 'third_party/fonts/方正像素16.ttf'), 16)


def tpl(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def show(name, arr):
    for r in range(arr.shape[0]):
        print('   %2d %s' % (r, ''.join('#' if arr[r, c] else '.' for c in range(arr.shape[1]))))


# 重复映射检查
rev = {}
for ch, p in cs.enc_pair.items():
    rev.setdefault(tuple(p), []).append(ch)
dups = {k: v for k, v in rev.items() if len(v) > 1}
print('对偶码重复映射:', dups or '无')
revs = {}
for ch, b in cs.enc_single.items():
    revs.setdefault(b, []).append(ch)
print('单字节码重复映射:', {k: v for k, v in revs.items() if len(v) > 1} or '无')

SPECIAL = [(ch, tuple(p)) for ch, p in cs.enc_pair.items() if not ('\u4e00' <= ch <= '\u9fff')]
print('非汉字对偶码 %d 个' % len(SPECIAL))
for ch, p in sorted(SPECIAL, key=lambda kv: tcslib.pair_slot(*kv[1])):
    slot = tcslib.pair_slot(*p)
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    w = ink[y:y + 16, x:x + 16]
    t = tpl(ch)
    n = int(w.sum())
    tn = int(t.sum())
    d = int((w != t).sum())
    miss = int((t & ~w).sum())
    extra = int((w & ~t).sum())
    print('%-2s %02X%02X slot=%4d (row%2d col%2d) 格=(%4d,%3d) 墨=%3d 模板墨=%3d 差异=%3d '
          '(模板有盘上无=%3d 盘上有模板无=%3d)' % (ch, p[0], p[1], slot, slot // 62, slot % 62,
                                                 x, y, n, tn, d, miss, extra))
    if ch in '±®µ':
        print('  -- 盘上引擎格:'); show(ch, w)
        print('  -- TTF 模板:'); show(ch, t)
