# -*- coding: utf-8 -*-
"""r51 探针⑤: y=482 带 (单字节码 0x80..0x9C) 的盘上像素 —— 是"别人"还是"flat 位置的自己"? 只读。

三问:
  Q1 记录窗 (u0,482,16x16) 的**引擎图**内容 == 本字 16px 模板吗?  (上一探针: 否)
  Q2 同一窗在 **flat 容器图**里 == 本字模板吗?                  (若是 ⇒ 历史写入用了 flat 坐标)
  Q3 它到底像 charset 里的哪个字?                              (辨认: 最小异或)
"""
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
import repack_font
from PIL import Image, ImageDraw, ImageFont

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
font = dump_font.load_font(ISO)
faces = font['faces']
am = font['atlas']
A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
eng = A.eng
flat = np.zeros((am['h'], am['w']), bool)
stride = am['w'] // 2
n = min(len(A.cont) // stride, am['h'])
raw = np.frombuffer(bytes(A.cont[:n * stride]), np.uint8).reshape(n, stride)
flat[:n, 0::2] = (raw & 0x0F) == 0
flat[:n, 1::2] = (raw >> 4) == 0
print('engine ink=%d  flat ink=%d' % (int(eng.sum()), int(flat.sum())))

fnt = ImageFont.truetype(TTF, 16)
_tc = {}


def tpl(ch):
    if ch in _tc:
        return _tc[ch]
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    w = np.asarray(img)[8:24, 8:24] < 128
    _tc[ch] = w if w.any() else None
    return _tc[ch]


cs = tcslib.Charset()
recs = [x for x in faces if x[0] == 'default'][0][2]

print()
print('=== Q1/Q2: 28 个记录窗在 引擎图 / flat 图 里 vs 本字模板 ===')
print('code ch   rec(u0,v0)            engine:墨/差异   flat:墨/差异   模板墨')
rows = []
for c in sorted(cs.codes):
    if not (0x80 <= c <= 0x9C) or c == 0x92:
        continue
    ch = cs.codes[c]
    r = recs[c - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    t = tpl(ch)
    if t is None or (u1 - u0, v1 - v0) != (16, 16):
        print('%02X %s 跳过 (模板空或记录非16x16 %s)' % (c, ch, (u0, v0, u1, v1)))
        continue
    e = eng[v0:v1, u0:u1]
    f = flat[v0:v1, u0:u1]
    rows.append((c, ch, (u0, v0), int(e.sum()), int((e ^ t).sum()),
                 int(f.sum()), int((f ^ t).sum()), int(t.sum())))
    print('%02X %s  (%3d,%3d)-(%3d,%3d)   %3d / %3d      %3d / %3d     %3d'
          % (c, ch, u0, v0, u1, v1, rows[-1][3], rows[-1][4], rows[-1][5], rows[-1][6], rows[-1][7]))
ok_e = sum(1 for x in rows if x[4] == 0)
ok_f = sum(1 for x in rows if x[6] == 0)
print('=> 引擎图口径 0 差异: %d/%d ; flat 口径 0 差异: %d/%d' % (ok_e, len(rows), ok_f, len(rows)))

print()
print('=== Q3: 引擎图里那块到底是谁 (全体对偶+单字节字模板辨认, 取最小异或) ===')
allch = [(ch, 'pair') for ch in cs.enc_pair] + [(ch, 'single') for ch in cs.enc_single]
for (c, ch, (u0, v0), ei, ed, fi, fd, ti) in rows[:8]:
    e = eng[v0:v0 + 16, u0:u0 + 16]
    best = []
    for (ch2, _k) in allch:
        t2 = tpl(ch2)
        if t2 is None:
            continue
        d = int((e ^ t2).sum())
        best.append((d, ch2))
    best.sort()
    print('%02X %s (本字差异 %d) → 最像: %s' % (c, ch, ed,
          ' '.join('%s:%d' % (b[1], b[0]) for b in best[:5])))
