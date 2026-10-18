# -*- coding: utf-8 -*-
r"""p10_read_screen.py — 实拍图逐行量化 (行带自动切分 + 按标签宽度左对齐取"字形区")。

正文框每行 = `<标签>: <3 个汉字>`; ASCII 字 8px + 空格 3px (与 tcslib W_ASCII/W_SPACE 同源)。
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
DUMP = os.path.join(REPO, 'work', 'builds', 'GR_TEST_PROBE_LEAD', 'temp', 'dump_probe')
SRC = os.path.join(DUMP, 'probe_page.png')
OUT_ZOOM = os.path.join(DUMP, 'probe_page_zoom.png')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

im = Image.open(SRC).convert('RGB')
px = np.asarray(im)
H, W, _ = px.shape
bright = px.mean(axis=2) > 120
X0, X1, Y0, Y1 = 28, 285, 118, 362
rows = bright[Y0:Y1, X0:X1].any(axis=1)
raw, i = [], 0
while i < len(rows):
    if rows[i]:
        j = i
        while j + 1 < len(rows) and rows[j + 1]:
            j += 1
        raw.append((Y0 + i, Y0 + j))
        i = j + 1
    else:
        i += 1
# 行高 ≈ 16px; 太高的带是"两行粘在一起" ⇒ 均分
bands = []
for (a, b) in raw:
    n = max(1, int(round((b - a + 1) / 16.0)))
    for t in range(n):
        bands.append((a + round((b - a + 1) * t / n), a + round((b - a + 1) * (t + 1) / n) - 1))
print('实拍图 %dx%d; 正文框 (%d..%d, %d..%d); 行带切分 → %d 段'
      % (W, H, X0, X1, Y0, Y1, len(bands)))

LABELS = ['PROBE', 'O', 'AD', 'AE', 'B0', 'B1', 'S']
ASCII, SPACE = 8.0, 3.0
recs = []
for k, (a, b) in enumerate(bands):
    seg = bright[a:b + 1, X0:X1]
    cols = np.where(seg.any(axis=0))[0]
    if not len(cols):
        continue
    xs, xe = X0 + cols[0], X0 + cols[-1]
    if xe - xs < 12:                       # 滚动条箭头等杂物
        print('  [%d] y=%3d..%3d x=%3d..%3d 宽 %2d px → 不是文字, 跳过' % (k, a, b, xs, xe, xe - xs + 1))
        continue
    lab = LABELS[len(recs)] if len(recs) < len(LABELS) else '?'
    gx0 = int(round(xs + (len(lab) + 1) * ASCII + SPACE))       # 标签 + ':' + 空格
    zone = bright[a:b + 1, gx0:xe + 1]
    recs.append(dict(lab=lab, a=a, b=b, xs=xs, xe=xe, gx0=gx0, zw=zone.shape[1], zone=zone))
    print('  [%d] %-6s y=%3d..%3d  x=%3d..%3d  字形区 x=%3d..%3d 宽 %3d px'
          % (len(recs) - 1, lab, a, b, xs, xe, gx0, xe, zone.shape[1]))

print('\n== 字形区两两比较 (基准 = O 行 = 现役码位) ==')


def norm(m):
    return np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((64, 16),
                                                                        Image.BILINEAR)) > 96


base = None
for r in recs:
    if r['lab'] == 'O' and base is None:
        base = norm(r['zone'])
        r['d'] = 0
        continue
    r['d'] = int((norm(r['zone']) != base).sum()) if base is not None else -1

for r in recs:
    lab, d = r['lab'], r['d']
    v = ''
    if lab == 'O':
        v = '(基准: 现役对偶码)'
    elif lab in ('AD', 'AE', 'B0'):
        v = ('★ 与对照**同一字形组** ✓' if d <= 24
             else '✗ 不同 (%d px)' % d)
    elif lab == 'B1':
        v = ('★ 与对照**明显不同** ⇒ 0xB1 不是 lead ✓' if d > 24 else '?? 居然相同')
    elif lab == 'S':
        v = '单字节行 (0xB2/0xB1/0xB5) —— 看图判读'
    print('  %-6s 宽 %3d px  与对照差异 %3d px  %s' % (lab, r['zw'], d, v))

crop = im.crop((X0 - 4, Y0 - 10, X1 + 4, Y1 + 8))
crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
crop.save(OUT_ZOOM)
print('\n已写放大图 %s (%dx%d)' % (OUT_ZOOM, crop.width, crop.height))
