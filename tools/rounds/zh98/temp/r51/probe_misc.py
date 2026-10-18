# -*- coding: utf-8 -*-
"""r51 探针③b: ç/ñ / 滚动三角 / 单字节 16x16 记录 vs 模板; 并统计"模板缺字"。只读。"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib
import dump_font
from PIL import Image, ImageDraw, ImageFont

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
font = dump_font.load_font(ISO)
faces = font['faces']
atlas = font['atlas']
gray = dump_font.atlas_gray(atlas, view='engine')
ink = (np.frombuffer(gray, np.uint8).reshape(atlas['h'], atlas['w']) == 0)
fnt = ImageFont.truetype(TTF, 16)


def tpl(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    win = a[8:24, 8:24] < 128
    over = (a < 128)
    oy, ox = np.where(over)
    if len(oy) and (oy.min() < 8 or ox.min() < 8 or oy.max() >= 24 or ox.max() >= 24):
        print('   [越窗] %r 墨 x%d..%d y%d..%d' % (ch, ox.min() - 8, ox.max() - 8,
                                                 oy.min() - 8, oy.max() - 8))
    return win


def bbox(m):
    if not m.any():
        return 'empty'
    y, x = np.where(m)
    return 'x%d..%d y%d..%d' % (x.min(), x.max(), y.min(), y.max())


nm, fld, recs = faces[tcslib.FONT_FACE_DEFAULT]
cs = tcslib.Charset()

print('=== ç/ñ (7x13) 与滚动三角 ===')
for c in (0xE7, 0xF1, 0x7B, 0x7D):
    ch = chr(c) if c < 0x80 else chr(c)
    r = recs[c - 0x20]
    sub = ink[r[3]:r[5], r[2]:r[4]]
    t = tpl(ch)
    print('code %02X %r rec=(%d,%d,%d,%d) %s 墨=%d %s | 模板墨=%d %s'
          % (c, ch, r[2], r[3], r[4], r[5], sub.shape, int(sub.sum()), bbox(sub),
             int(t.sum()), bbox(t)))
    for y in range(sub.shape[0]):
        print('     盘 %s   模板[0:7] %s'
              % (''.join('#' if sub[y, x] else '.' for x in range(sub.shape[1])),
                 ''.join('#' if t[y, x] else '.' for x in range(7))))

print()
print('=== 模板缺字 (charset 全部字 + ASCII + 单字节) ===')
miss = []
for ch in sorted(set(list(cs.enc_pair) + list(cs.enc_single))):
    if not tpl(ch).any():
        miss.append(ch)
print('对偶+单字节里模板为空的: %d 个 -> %s' % (len(miss), ''.join(miss)))
missa = [chr(c) for c in range(0x21, 0x7F) if not tpl(chr(c)).any()]
print('ASCII 0x21..0x7E 里模板为空的: %s' % (missa if missa else '无'))

print()
print('=== 对偶格: 全部在用字与模板逐像素 (紧阈值) ===')
bad = []
n = 0
for ch, (b1, b2) in sorted(cs.enc_pair.items(), key=lambda kv: tcslib.pair_slot(*kv[1])):
    if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
        continue
    n += 1
    slot = tcslib.pair_slot(b1, b2)
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    sub = ink[y:y + 16, x:x + 16]
    t = tpl(ch)
    if not t.any():
        continue
    d = int((sub ^ t).sum())
    if d:
        bad.append((ch, '%02X%02X' % (b1, b2), slot, int(sub.sum()), int(t.sum()), d))
print('比对 %d 个对偶字; 有差异 %d 个' % (n, len(bad)))
for b in bad:
    print('   %s %s slot=%d 盘墨=%d 模板墨=%d 差异=%d' % b)

print()
print('=== 单字节码: FT 记录 16x16 vs 模板 ===')
bad2 = []
n2 = 0
for ch, c in sorted(cs.enc_single.items(), key=lambda kv: kv[1]):
    r = recs[c - 0x20]
    if r[4] - r[2] != 16 or r[5] - r[3] != 16:
        print('   [跳过] %r 0x%02X 记录 (%d,%d,%d,%d)' % (ch, c, r[2], r[3], r[4], r[5]))
        continue
    n2 += 1
    sub = ink[r[3]:r[5], r[2]:r[4]]
    t = tpl(ch)
    if not t.any():
        print('   [模板空] %r 0x%02X' % (ch, c))
        continue
    d = int((sub ^ t).sum())
    if d:
        bad2.append((ch, '%02X' % c, (r[2], r[3]), int(sub.sum()), int(t.sum()), d))
print('比对 %d 个单字节字; 有差异 %d 个' % (n2, len(bad2)))
for b in bad2:
    print('   %s %s cell=%s 盘墨=%d 模板墨=%d 差异=%d' % b)

print()
print('=== ASCII: 记录 (8x16) vs 模板左 8 列 ===')
bad3 = []
for c in range(0x21, 0x7F):
    ch = chr(c)
    if c in (0x7B, 0x7D):
        continue
    r = recs[c - 0x20]
    w = r[4] - r[2]
    sub = ink[r[3]:r[5], r[2]:r[4]]
    t = tpl(ch)[:, :w]
    if not t.any():
        print('   [模板空] %r' % ch)
        continue
    d = int((sub ^ t).sum())
    if d:
        bad3.append((ch, '%02X' % c, int(sub.sum()), int(t.sum()), d))
print('比对 92 个 ASCII; 有差异 %d 个' % len(bad3))
for b in bad3:
    print('   %s %s 盘墨=%d 模板墨=%d 差异=%d' % b)
