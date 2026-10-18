# -*- coding: utf-8 -*-
r"""render_de_glyph.py — 用系统黑体按现役配方渲「嘚」(U+561A)，补上唯一缺字

现役配方（tools/font_pipeline/gen_font16.py 的 render16）:
   ImageFont.truetype(ttf, 16) 原点画在 (8,8) ⇒ 取 canvas[8:24, 8:24] ⇒ 阈值 <128 为墨
输出: 16×16 位图 + ASCII 预览 + 4bpp bin（墨=0x0 / 底=0x1，与 PS2 现役图集一致）
"""
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(OUT, exist_ok=True)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def render16(ttf, ch, thresh=128):
    f = ImageFont.truetype(ttf, 16)
    im = Image.new('L', (32, 32), 0)
    d = ImageDraw.Draw(im)
    d.text((8, 8), ch, fill=255, font=f)
    win = im.crop((8, 8, 24, 24))
    px = [[1 if win.getpixel((x, y)) < thresh else 0 for x in range(16)] for y in range(16)]
    return px


def show(name, px):
    ink = sum(sum(r) for r in px)
    print('  %s : 墨 %d / 256' % (name, ink))
    for r in px:
        print('     ' + ''.join('#' if v else '.' for v in r))
    return ink


def to4bpp(px):
    out = bytearray(128)
    for y in range(16):
        for x in range(0, 16, 2):
            out[(y * 16 + x) // 2] = px[y][x] | (px[y][x + 1] << 4)
    return bytes(out)


fang = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
sysdir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')

print('=== 对照: 方正像素16 渲染的字（用于比对风格）===')
for ch in ('得', '的'):
    show('方正像素16 %s' % ch, render16(fang, ch))
print()
print('=== 缺字: 用系统字体渲染「嘚」===')
best = None
for fn in ('simhei.ttf', 'msyh.ttc', 'simsun.ttc', 'Deng.ttf'):
    p = os.path.join(sysdir, fn)
    if not os.path.exists(p):
        continue
    try:
        px = render16(p, '嘚')
        ink = show('%s 嘚' % fn, px)
        if best is None or ink > 0:
            if best is None:
                best = (fn, px)
    except Exception as e:
        print('  %s 失败: %s' % (fn, str(e)[:60]))

if best:
    fn, px = best
    out = os.path.join(OUT, 'glyph_561A_4bpp.bin')
    open(out, 'wb').write(to4bpp(px))
    print()
    print('★ 选用 %s 的渲染结果写出: %s (%d B)' % (fn, out, 128))
    print('  ⇒ 这一个字的来源确定，**不必改译文** ✓')
