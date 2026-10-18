# -*- coding: utf-8 -*-
"""r50 临时探针: 看 GR_ZH97 图集里 孙/宁/宇 (row20 col33/34/35) 的实际像素, 并对照 TTF 模板。"""
import io
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

ISO = os.path.join(REPO, 'work/builds/GR_ZH97/GR_ZH97.iso')
font = dump_font.load_font(ISO)
gray = dump_font.atlas_gray(font['atlas'], view='engine')
W, H = font['atlas']['w'], font['atlas']['h']
A = np.frombuffer(gray, np.uint8).reshape(H, W)
ink = (A == 0)
print('atlas %dx%d ink=%d' % (W, H, ink.sum()))

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)


def tpl(ch):
    img = Image.new('L', (32, 32), 255)
    d = ImageDraw.Draw(img)
    d.text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    return a[8:24, 8:24] < 128


def show(name, arr, y0_off=None):
    print('--', name)
    for r in range(arr.shape[0]):
        print('   %2d %s' % (r, ''.join('#' if arr[r, c] else '.' for c in range(arr.shape[1]))))


import json
d = json.load(io.open(os.path.join(REPO, 'work/builds/GR_ZH98/temp/font_recycle_backup.json'),
                      encoding='utf-8'))
import base64


def from_bk(ch):
    b = base64.b64decode(d['glyphs'][ch]['bits'])
    return np.array([[(b[r * 2] >> (15 - c)) & 1 for c in range(16)] for r in range(16)], bool)


for ch in '孙宁宇':
    slot = tcslib.pair_slot(*d['glyphs'][ch]['pair'])
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    print('=== %s slot=%d cell=(%d,%d) row=%d col=%d' % (ch, slot, x, y, slot // 62, slot % 62))
    cell = ink[y:y + 16, x:x + 16]
    show('盘上 GR_ZH97 引擎格', cell)
    show('备份里存的位图(同一格)', from_bk(ch))
    show('TTF 模板 (em 窗)', tpl(ch))
    # 窗下方 4 行 (看有没有渗漏/截断)
    below = ink[y - 2:y + 20, x:x + 16]
    show('上下各扩 2 行 (y-2..y+19)', below)
    print('   窗内墨=%d 第15行墨=%d 窗下第1行(y+16)墨=%d 第2行(y+17)墨=%d'
          % (cell.sum(), cell[15].sum(), ink[y + 16, x:x + 16].sum() if y + 16 < H else -1,
             ink[y + 17, x:x + 16].sum() if y + 17 < H else -1))
