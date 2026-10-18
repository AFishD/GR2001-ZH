# -*- coding: utf-8 -*-
"""r51 探针⑫: GR_ZH98 → GR_ZH100 的图集差异逐格定位 (Lead 的修复到底写了哪几格, 稳 为什么还错)。只读。"""
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

FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ, 16)
_c = {}


def tpl(ch):
    if ch in _c:
        return _c[ch]
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    w = np.asarray(img)[8:24, 8:24] < 128
    _c[ch] = w if w.any() else None
    return _c[ch]


def eng_of(iso):
    f = dump_font.load_font(iso)
    g = dump_font.atlas_gray(f['atlas'], view='engine')
    a = f['atlas']
    return (np.frombuffer(g, np.uint8).reshape(a['h'], a['w']) == 0), f


E98, f98 = eng_of(os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso'))
E100, f100 = eng_of(os.path.join(REPO, 'work', 'builds', 'GR_ZH100', 'GR_ZH100.iso'))
print('GR_ZH98 墨=%d  GR_ZH100 墨=%d  差=%+d' % (E98.sum(), E100.sum(), E100.sum() - E98.sum()))
d = E98 ^ E100
ys, xs = np.where(d)
print('改动像素 %d; 行范围 %d..%d, 列范围 %d..%d' % (len(ys), ys.min(), ys.max(), xs.min(), xs.max()))
# 按 16x16 格归组
cells = {}
for y, x in zip(ys.tolist(), xs.tolist()):
    cells.setdefault((y // 16 * 16, x // 16 * 16), 0)
    cells[(y // 16 * 16, x // 16 * 16)] += 1
print('涉及 %d 个 16x16 格块:' % len(cells))
for k in sorted(cells):
    print('   块(行%d,列%d) = y%3d x%3d : %d px' % (k[0] // 16, k[1] // 16, k[0], k[1], cells[k]))

cs = tcslib.Charset()
recs = [x for x in f100['faces'] if x[0] == 'default'][0][2]
print()
print('=== 28 个目标窗在 GR_ZH100 上是否正确 ===')
bad = []
for c in sorted(cs.codes):
    if not (0x80 <= c <= 0x9C) or c == 0x92:
        continue
    ch = cs.codes[c]
    r = recs[c - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    sub = E100[v0:v1, u0:u1]
    t = tpl(ch)
    diff = int((sub ^ t).sum()) if t is not None else -1
    ok = 'OK ' if diff == 0 else '!! '
    if diff != 0:
        bad.append((c, ch, u0, v0, diff))
    print('  %s%02X %s rec=(%3d,%3d) 墨=%3d 模板=%3d 差异=%3d'
          % (ok, c, ch, u0, v0, int(sub.sum()), int(t.sum()) if t is not None else -1, diff))
print()
print('不正确的: %s' % (bad if bad else '无'))
# 稳 的模板在整张图上有没有
t = tpl('稳')
from numpy.lib.stride_tricks import sliding_window_view
v = sliding_window_view(E100.astype(np.uint8), (16, 16)).reshape(-1, 256)
tv = t.reshape(-1).astype(np.int32)
inter = v.astype(np.int32) @ tv
union = v.sum(1).astype(np.int32) + int(tv.sum()) - inter
iou = inter / np.maximum(union, 1)
cand = np.argsort(-iou)[:5]
ncol = E100.shape[1] - 16 + 1
print()
print('=== 稳 的模板在全盘最像的 5 处 ===')
for i in cand:
    y, x = divmod(int(i), ncol)
    ex = int((E100[y:y + 16, x:x + 16] ^ t).sum())
    print('   (%4d,%3d) IoU=%.3f 精确差异=%d' % (x, y, iou[i], ex))
print()
print('=== 稳 的目标窗 (432,482) 在 GR_ZH98 / GR_ZH100 的位图 ===')
for nm, E in (('ZH98', E98), ('ZH100', E100)):
    print(' %s:' % nm)
    for row in E[482:498, 432:448]:
        print('    |' + ''.join('#' if v_ else '.' for v_ in row) + '|')
print(' 模板 稳:')
for row in t:
    print('    |' + ''.join('#' if v_ else '.' for v_ in row) + '|')
