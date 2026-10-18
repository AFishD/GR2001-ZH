# -*- coding: utf-8 -*-
r"""lead_force_stable.py — 强制把 0x9C(稳) 的模板写进 (432,482), 并回读验证

为什么需要强制: 主补丁在 0x9C 上判定 diff=0(认为已对), 但独立工具与 Lead 直读都显示该格 IoU=0.24。
本脚本不做 diff 判断, 直接写入, 用于定位/收口。
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D                                   # noqa: E402
import glyph_geometry as G                              # noqa: E402
from patch_zh94_glyph_align import Atlas                # noqa: E402

SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH100', 'GR_ZH100.iso')
DST = os.path.join(REPO, 'work', 'builds', 'GR_ZH100', 'temp', 'stable_fixed.iso')
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')

fnt = ImageFont.truetype(FZ16, 16)
img = Image.new('L', (32, 32), 255)
ImageDraw.Draw(img).text((8, 8), '稳', font=fnt, fill=0)
tgt = np.asarray(img)[8:24, 8:24] < 128
print('稳 模板墨点 %d ; 与 G.Templates 一致: %s'
      % (int(tgt.sum()), bool((tgt == G.Templates().get('稳')).all())))

w = D.load_font(SRC)
ad, pak_e = w['atlas'], w['pak_e']
PX, PSZ, iso_off = ad['px_off'], ad['px_size'], pak_e['iso_off']
A = Atlas(bytearray(ad['pak']), PX, PSZ)
En, _ = A.decode_engine()

U0, V0 = 432, 482
cur = En[V0:V0 + 16, U0:U0 + 16].astype(bool)
print('写前: 该格墨点 %d ; 与稳模板 diff=%d IoU=%.4f'
      % (int(cur.sum()), int(np.logical_xor(cur, tgt).sum()),
         float(np.logical_and(cur, tgt).sum()) / max(1, int(np.logical_or(cur, tgt).sum()))))
print('写前: 该格最像的字 =', end=' ')
best = []
for ch in list(G.Templates()._cache.keys()):
    t = G.Templates().get(ch)
    if t is not None:
        inter = int(np.logical_and(cur, t).sum()); uni = int(np.logical_or(cur, t).sum())
        if uni:
            best.append((inter / uni, ch))
best.sort(reverse=True)
print(', '.join('%s %.3f' % (c, i) for i, c in best[:3]))

En[V0:V0 + 16, U0:U0 + 16] = tgt
changed = np.where(En != A.eng)
print('强制写入像素数: %d' % len(changed[0]))
for y, x in zip(changed[0].tolist(), changed[1].tolist()):
    A.set_px(int(x), int(y), bool(En[y, x]), 1)
back, _c = A.decode_engine()
assert (back == En).all()
shutil.copyfile(SRC, DST)
with open(DST, 'r+b') as f:
    f.seek(iso_off + PX)
    f.write(bytes(A.nib))
print('→ %s (尺寸 %d, 原 %d)' % (os.path.relpath(DST, REPO), os.path.getsize(DST), os.path.getsize(SRC)))

g = np.frombuffer(D.atlas_gray(D.load_font(DST)['atlas'], view='engine'),
                  dtype=np.uint8).reshape(ad['h'], ad['w'])
cur2 = (g[V0:V0 + 16, U0:U0 + 16] < 128)
print('回读(dump_font 口径): diff=%d IoU=%.4f %s'
      % (int(np.logical_xor(cur2, tgt).sum()),
         float(np.logical_and(cur2, tgt).sum()) / max(1, int(np.logical_or(cur2, tgt).sum())),
         '✓' if (cur2 == tgt).all() else '✗'))
