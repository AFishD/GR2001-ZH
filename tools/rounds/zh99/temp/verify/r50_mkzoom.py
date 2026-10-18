# -*- coding: utf-8 -*-
r"""r50_mkzoom.py — 证据图: 旧盘 row20 那一行「盘上像素 vs 16px 模板 vs 缺失像素(红) vs 现役盘」。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402

OUT = os.path.join(HERE, 'zoom_truncation.png')
FZ16 = os.path.join(REPO, 'third_party/fonts/方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)
Y0, Y1, X0, X1, SC = 366, 390, 448, 592, 12


def templ(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def eng(rel):
    f = dump_font.load_font(os.path.join(REPO, rel))
    g = dump_font.atlas_gray(f['atlas'], view='engine')
    w, h = f['atlas']['w'], f['atlas']['h']
    return (np.frombuffer(g, np.uint8).reshape(h, w) == 0)


A97 = eng('work/builds/GR_ZH97/GR_ZH97.iso')
A99 = eng('work/builds/GR_ZH99/GR_ZH99.iso')
cs97 = tcslib.Charset(os.path.join(REPO, 'work/builds/GR_ZH98/temp/charset_before_font_cleanup.json'))
slot2ch = dict((tcslib.pair_slot(*p), ch) for ch, p in cs97.enc_pair.items())


def tile(a, tint=None):
    rgb = np.zeros(a.shape + (3,), np.uint8)
    rgb[:, :] = (255, 255, 255)
    rgb[a] = (0, 0, 0)
    if tint is not None:
        rgb[tint] = (230, 30, 30)
    im = Image.frombytes('RGB', (a.shape[1], a.shape[0]), rgb.tobytes())
    return im.resize((a.shape[1] * SC, a.shape[0] * SC), Image.NEAREST)


band = np.zeros((Y1 - Y0, X1 - X0), bool)
miss = np.zeros_like(band)
for col in range(28, 37):
    ch = slot2ch.get(20 * 62 + col)
    if not ch:
        continue
    t = templ(ch)
    x, y = col * 16 - X0, 370 - Y0
    band[y:y + 16, x:x + 16] = t
    miss[y:y + 16, x:x + 16] = t & ~A97[370:386, col * 16:col * 16 + 16]
tiles = [('① GR_ZH97 盘上像素 (row20 col28..36)', tile(A97[Y0:Y1, X0:X1])),
         ('② 16px 模板 (方正像素16.ttf, 同一位置)', tile(band)),
         ('③ 模板有墨 / 盘上没有的像素 (红 = 被截掉的那一行)', tile(band, miss)),
         ('④ GR_ZH99 同位置 (这些字已回收 ⇒ 空白)', tile(A99[Y0:Y1, X0:X1]))]
lab = 34
W = max(t[1].size[0] for t in tiles)
H = sum(t[1].size[1] + lab + 10 for t in tiles) + 56
canvas = Image.new('RGB', (W + 24, H), (245, 245, 245))
d = ImageDraw.Draw(canvas)
try:
    f = ImageFont.truetype(FZ16, 14)
except Exception:                                          # noqa: BLE001
    f = ImageFont.load_default()
y = 8
d.text((10, y), 'round50 证据图: 旧盘 row20 col28..36 (夏 奈 奋 姚 娜 孙 宁 宇 沈) —— '
                '底行被截断 / 现役盘上这些字已回收', fill=(0, 0, 0), font=f)
y += 26
for (cap, im) in tiles:
    d.text((12, y), cap, fill=(0, 0, 0), font=f)
    canvas.paste(im, (12, y + lab - 12))
    d.rectangle([12, y + lab - 12, 12 + im.size[0] - 1, y + lab - 12 + im.size[1] - 1],
                outline=(120, 120, 120))
    y += im.size[1] + lab + 10
canvas.save(OUT)
print('→', OUT, canvas.size)
