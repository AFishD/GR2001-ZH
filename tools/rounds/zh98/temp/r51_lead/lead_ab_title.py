# -*- coding: utf-8 -*-
r"""lead_ab_title.py — 把 A/B 差异那一个字裁出来放大对照 (GR_ZH98 vs 候选盘)"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

A = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'verify', 'r49_doc_zh98')
B = os.path.join(REPO, 'work', 'builds', 'cand_both', 'temp', 'dump_r51_doc_cand')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r51', 'lead_ab_title')
os.makedirs(OUT, exist_ok=True)

for tag, d in (('A_ZH98', A), ('B_cand', B)):
    fs = sorted(f for f in os.listdir(d) if f.startswith('snap_'))
    print('%s: %d 帧' % (tag, len(fs)))

# 取差异帧, 裁 (319,80)-(326,93) 前后各留 90x20 上下文
BOX = (240, 62, 420, 110)
S = 6
tiles = []
for tag, d in (('ZH98', A), ('候选盘', B)):
    p = os.path.join(d, 'snap_f00027300.png')
    if not os.path.isfile(p):
        print('缺 %s' % p)
        continue
    im = Image.open(p).convert('RGB')
    crop = im.crop(BOX)
    crop = crop.resize((crop.width * S, crop.height * S), Image.NEAREST)
    tiles.append((tag, crop))
    print('%s 裁图 %s -> %dx%d' % (tag, os.path.basename(p), crop.width, crop.height))

if len(tiles) == 2:
    w = max(t.width for _, t in tiles)
    h = sum(t.height for _, t in tiles) + 8
    sheet = Image.new('RGB', (w, h), (255, 255, 255))
    y = 0
    for tag, t in tiles:
        sheet.paste(t, (0, y))
        y += t.height + 8
    p = os.path.join(OUT, 'ab_title_zoom.png')
    sheet.save(p)
    print('→ %s (%dx%d) 上=ZH98, 下=候选盘' % (os.path.relpath(p, REPO), sheet.width, sheet.height))
    # 同时给出差异像素的 ASCII
    a = Image.open(os.path.join(A, 'snap_f00027300.png')).convert('L')
    b = Image.open(os.path.join(B, 'snap_f00027300.png')).convert('L')
    pa, pb = a.load(), b.load()
    print()
    print('差异区 (x 319..326, y 80..93) 的墨点对照  # = 墨:')
    for y in range(78, 96):
        ra = ''.join('#' if pa[x, y] < 128 else '.' for x in range(300, 345))
        rb = ''.join('#' if pb[x, y] < 128 else '.' for x in range(300, 345))
        mark = ' <<<' if ra != rb else ''
        print('  y=%3d  A %s%s' % (y, ra, mark))
        print('         B %s' % rb)
