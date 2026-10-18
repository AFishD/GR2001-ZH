# -*- coding: utf-8 -*-
r"""p4_ftsheet.py — 把现役盘 FT 记录表里若干**单字节码**的采样窗渲染成参考图。

用途: 探针实拍时, 若某个字节被引擎当单字节画, 屏幕上出现的就应该是这里的某一张。
不写盘, 只出 PNG。
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import dump_font as D                                                     # noqa: E402
import tcslib                                                             # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
OUT = os.path.join(HERE, 'p4_ftsheet.png')
CODES = [0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xDD, 0xD0, 0xD1, 0xD2, 0xAE, 0xAF, 0xB0,
         0xA1, 0xA2, 0xE7, 0xF1, 0x20, 0x3A]

f = D.load_font(ISO)
atlas, faces = f['atlas'], f['faces']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, 'engine'), dtype=np.uint8).reshape(H, W)
ink = gray == 0

PAD, SC = 4, 8
cw, chh = 16, 16
cols = len(CODES)
sheet = Image.new('RGB', (PAD + cols * (cw * SC + PAD), 96 + chh * SC + PAD), (255, 255, 255))
d = ImageDraw.Draw(sheet)
cs = tcslib.Charset()

rows = []
for code in CODES:
    idx = code - 0x20
    line = []
    for (nm, _fld, recs) in faces:
        if not (0 <= idx < len(recs)):
            line.append(None)
            continue
        _b0, _b1, u0, v0, u1, v1 = recs[idx]
        if u1 <= u0 or v1 <= v0:
            line.append((u0, v0, u1, v1, 0))
            continue
        n = int(ink[v0:v1, u0:u1].sum())
        line.append((u0, v0, u1, v1, n))
    rows.append((code, line))

print('码   ' + '  '.join('%-22s' % nm for nm, _f, _r in faces))
for code, line in rows:
    desc = '  '.join('(%d,%d,%d,%d)墨%3d' % t if t else '—' for t in line)
    single = cs.codes.get(code)
    print('0x%02X %s   charset单字节=%s' % (code, desc, single or '—'))

for i, (code, line) in enumerate(rows):
    ox = PAD + i * (cw * SC + PAD)
    d.text((ox, 4), '0x%02X' % code, fill=(0, 0, 0))
    ch = cs.codes.get(code)
    d.text((ox, 20), ch or '—', fill=(0, 0, 160))
    for j, t in enumerate(line):
        if t is None:
            continue
        u0, v0, u1, v1, n = t
        d.text((ox, 40 + j * 12), '%s %d' % (['lg', 'df', 'hg'][j], n), fill=(120, 120, 120))
        if n == 0:
            continue
        oy = 76
        for yy in range(min(chh, v1 - v0)):
            for xx in range(min(cw, u1 - u0)):
                if ink[v0 + yy, u0 + xx]:
                    d.rectangle([ox + xx * SC, oy + yy * SC,
                                 ox + (xx + 1) * SC - 1, oy + (yy + 1) * SC - 1], fill=(0, 0, 0))
        oy += 0
sheet.save(OUT)
print('\n已写 %s' % OUT)
