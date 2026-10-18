# -*- coding: utf-8 -*-
r"""v9b_cell.py — 「中」「斗」单格 修前/修后 对比 (高倍), 给报告当证据图。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw                                          # noqa: E402
from r47lib import load                                                   # noqa: E402
from PIL import ImageFont                                                 # noqa: E402

CELLS = [('中', 912, 338), ('斗', 944, 338)]
Z = 18
eng94 = load('GR_ZH94')['eng']
eng96 = load('GR_ZH96_fix')['eng']
W = 16 * Z
W2 = len(CELLS) * (W + 8)
im = Image.new('RGB', (W2, W * 2 + 40), (255, 255, 255))
d = ImageDraw.Draw(im)
d.text((4, 4), 'GR_ZH94 (修前): 每格最后一行 y=353 有上一代字形残留', fill=(0, 0, 0))
d.text((4, W + 24), 'GR_ZH96_fix (修后): 该行 = 方正像素16 模板', fill=(0, 0, 0))
for k, (ch, u0, v0) in enumerate(CELLS):
    for row, (eng, tag) in enumerate(((eng94, 'a'), (eng96, 'b'))):
        sub = eng[v0:v0 + 16, u0:u0 + 16]
        cell = Image.new('RGB', (16, 16), (255, 255, 255))
        px = cell.load()
        for y in range(16):
            for x in range(16):
                if sub[y, x]:
                    px[x, y] = (0, 0, 0)
                elif y == 15:
                    px[x, y] = (255, 235, 235)          # 溢出带行底色
        big = cell.resize((W, W), Image.NEAREST)
        im.paste(big, (k * (W + 8), 18 + row * (W + 24)))
        d.text((k * (W + 8) + 4, 18 + row * (W + 24) + W + 2), '%s @ (%d,%d)' % (ch, u0, v0),
               fill=(0, 0, 0))
p = os.path.join(HERE, 'cell_zhong_dou_ab.png')
im.save(p)
print('→ %s' % p)

# 顺带把 ASCII 也存一份 (报告里直接贴)
with open(os.path.join(HERE, 'cell_ascii.txt'), 'w', encoding='utf-8', newline='\n') as f:
    for ch, u0, v0 in CELLS:
        for tag, eng in (('GR_ZH94  ', eng94), ('GR_ZH96_fix', eng96)):
            f.write('=== %s %s (%d,%d) ===\n' % (ch, tag, u0, v0))
            for y in range(v0, v0 + 16):
                marks = ''.join('#' if eng[y, x] else '.' for x in range(u0, u0 + 16))
                f.write('  %3d |%s|%s\n' % (y, marks, '   ← 溢出带行 y=353' if y == 353 else ''))
print('→ cell_ascii.txt')
