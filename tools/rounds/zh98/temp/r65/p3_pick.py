# -*- coding: utf-8 -*-
r"""p3_pick.py — 挑对照字 (现役 charset 里 lead ≤ 0xAD 的对偶字), 报出它的 slot/格/墨量,
并把候选字形渲染成一张放大 PNG 供人眼确认 ("这确实是个正常的汉字")。"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                     # noqa: E402
import tcslib                                                             # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
OUT = os.path.join(HERE, 'p3_pick.png')
f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
ink = gray == 0
cs = tcslib.Charset()

CANDS = '我你好中国大小上下天地人山水火日月'
print('== 候选对照字 ==')
ok = []
for ch in CANDS:
    p = cs.enc_pair.get(ch)
    s = cs.enc_single.get(ch)
    if p:
        slot = tcslib.pair_slot(*p)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        n = int(ink[y:y + 16, x:x + 16].sum())
        print('  %s pair=%02X%02X slot=%4d row=%2d col=%2d cell=(%4d,%3d) 墨=%3d'
              % (ch, p[0], p[1], slot, slot // 62, slot % 62, x, y, n))
        if n >= 20 and p[0] <= 0xAD and slot <= 1174:
            ok.append((ch, p, slot, x, y, n))
    elif s:
        print('  %s 单字节码 0x%02X (不适合做对偶对照)' % (ch, s))
    else:
        print('  %s 不在 charset 里' % ch)

print('\n合格对照字 %d 个: %s' % (len(ok), ' '.join(c for c, *_ in ok)))

# ---- 渲染候选字形 (每个 16x16, 放大 6 倍) ----
pad = 6
cell = 16 * pad
img = Image.new('RGB', (cell * len(ok) + pad * (len(ok) + 1), cell + 40 + pad * 2), (255, 255, 255))
from PIL import ImageDraw                                                    # noqa: E402
d = ImageDraw.Draw(img)
for i, (ch, p, slot, x, y, n) in enumerate(ok):
    ox = pad + i * (cell + pad)
    oy = 40 + pad
    g = gray[y:y + 16, x:x + 16]
    for yy in range(16):
        for xx in range(16):
            if g[yy, xx] == 0:
                d.rectangle([ox + xx * pad, oy + yy * pad, ox + (xx + 1) * pad - 1,
                             oy + (yy + 1) * pad - 1], fill=(0, 0, 0))
    d.rectangle([ox, oy, ox + cell - 1, oy + cell - 1], outline=(255, 0, 0))
    d.text((ox, 6), ch, fill=(0, 0, 0))
    d.text((ox, 22), '%02X%02X' % p, fill=(0, 0, 160))
img.save(OUT)
print('已写 %s' % OUT)
