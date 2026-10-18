# -*- coding: utf-8 -*-
"""r51 探针⑥: 决定性判定 —— 28 个单字节码 (0x80..0x9C) 的字形到底在哪?
 (a) 段表; (b) ASCII 在引擎图/flat 图 哪个对得上; (c) 全图搜索这 28 个模板; (d) 对照 GR_ZH93/94/95/97。只读。"""
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

TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
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


def load(iso):
    font = dump_font.load_font(iso)
    am = font['atlas']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    g = dump_font.atlas_gray(am, view='engine')
    eng2 = (np.frombuffer(g, np.uint8).reshape(am['h'], am['w']) == 0)
    assert np.array_equal(eng2, A.eng), 'dump_font 引擎图 != repack_font 引擎图'
    flat = np.zeros((am['h'], am['w']), bool)
    stride = am['w'] // 2
    n = min(len(A.cont) // stride, am['h'])
    raw = np.frombuffer(bytes(A.cont[:n * stride]), np.uint8).reshape(n, stride)
    flat[:n, 0::2] = (raw & 0x0F) == 0
    flat[:n, 1::2] = (raw >> 4) == 0
    faces = font['faces']
    recs = [x for x in faces if x[0] == 'default'][0][2]
    return A, eng2, flat, recs, am


def find_all(img, t, tol=0):
    """在 img (bool HxW) 里滑窗找与 t (16x16) 零差异的位置。"""
    H, W = img.shape
    hits = []
    for y in range(0, H - 16 + 1):
        for x in range(0, W - 16 + 1):
            if int((img[y:y + 16, x:x + 16] ^ t).sum()) <= tol:
                hits.append((x, y))
    return hits


ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
A, eng, flat, recs, am = load(ISO)
print('GR_ZH98 段表 (首行, 数据偏移, 字节数):')
for s in A.segs:
    print('   row %3d  doff 0x%06X  bytes %6d  (%d 行)' % (s[0], s[1], s[2], s[2] // 512))
print('   flat_x_shift(452)=%d  flat_x_shift(482)=%d' % (tcslib.atlas_flat_x_shift(452),
                                                           tcslib.atlas_flat_x_shift(482)))
print()
print('ASCII 92 个: 引擎图 0 差异 / flat 图 0 差异')
for nm, img in (('engine', eng), ('flat', flat)):
    n_ok = 0
    for c in range(0x21, 0x7F):
        if c in (0x7B, 0x7D):
            continue
        r = recs[c - 0x20]
        sub = img[r[3]:r[5], r[2]:r[4]]
        t = tpl(chr(c))[:, :r[4] - r[2]]
        if int((sub ^ t).sum()) == 0:
            n_ok += 1
    print('   %-6s -> %d/92' % (nm, n_ok))

cs = tcslib.Charset()
print()
print('=== 28 个单字节码的字形在引擎图里到底有没有 (全图 0 差异搜索) ===')
for c in sorted(cs.codes):
    if not (0x80 <= c <= 0x9C) or c == 0x92:
        continue
    ch = cs.codes[c]
    r = recs[c - 0x20]
    u0, v0 = r[2], r[3]
    t = tpl(ch)
    if t is None:
        continue
    hits_e = find_all(eng, t)
    hits_f = find_all(flat, t)
    fx, fy = tcslib.atlas_flat_pos(u0, v0, am['w'])
    print('%02X %s rec=(%3d,%3d) | 引擎图命中 %s | flat 图命中 %s | flat_pos(rec)=(%d,%d)'
          % (c, ch, u0, v0, hits_e[:4] if hits_e else '无', hits_f[:4] if hits_f else '无', fx, fy))
