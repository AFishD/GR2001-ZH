# -*- coding: utf-8 -*-
r"""lead_diff_locate.py — 定位我的独立解析与工具渲染的 321 像素差异在哪"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
atlas = D.load_font(ISO)['atlas']
pak, px_off, W, H = atlas['pak'], atlas['px_off'], atlas['w'], atlas['h']
blob = pak[px_off:]
STRIDE, ROWS, SEGHDR = W // 2, 64, 48

img = bytearray(W * H)
seg, off = 0, 0
while off + SEGHDR + STRIDE * ROWS <= len(blob):
    off += SEGHDR
    y0 = seg * ROWS
    if y0 + ROWS > H:
        break
    for r in range(ROWS):
        row = blob[off + r * STRIDE: off + (r + 1) * STRIDE]
        base = (y0 + r) * W
        for bx, byte in enumerate(row):
            img[base + bx * 2] = 0 if (byte & 0xF) == 0 else 255
            img[base + bx * 2 + 1] = 0 if (byte >> 4) == 0 else 255
    off += STRIDE * ROWS
    seg += 1

# 工具自己的引擎图 (走它的正规路径)
tool = D.atlas_gray(atlas, view='engine')
print('我: %d 字节, 工具: %d 字节' % (len(img), len(tool)))

diffs = [(x, y) for y in range(H) for x in range(W)
         if (img[y * W + x] < 128) != (tool[y * W + x] < 128)]
print('差异像素: %d' % len(diffs))
if diffs:
    xs = [d[0] for d in diffs]
    ys = [d[1] for d in diffs]
    print('  x 范围 %d..%d ; y 范围 %d..%d' % (min(xs), max(xs), min(ys), max(ys)))
    # 按行分布
    from collections import Counter
    cy = Counter(y for _, y in diffs)
    print('  按 y 行 (前 12):', sorted(cy.items())[:12])
    print('  涉及 y 行数:', len(cy))
    # 只看这些像素: 我 vs 工具
    print('  抽样 (x, y, mine, tool):')
    for (x, y) in diffs[:10]:
        print('    (%4d,%3d)  mine=%3d tool=%3d' % (x, y, img[y * W + x], tool[y * W + x]))
    # 差异是否集中在段边界
    print('  落在段边界 (y%%64 == 0/1/62/63) 的比例: %.1f%%' %
          (100.0 * sum(1 for _, y in diffs if y % 64 in (0, 1, 62, 63)) / len(diffs)))
# 顺便看看 blob 里到底有几个段头
print()
print('blob 长度 %d ; 按 (48+64*512)=%d 算段数 = %.3f' % (len(blob), 48 + 64 * 512, len(blob) / (48 + 64 * 512)))
print('剩余尾部字节: %d' % (len(blob) - seg * (48 + 64 * 512)))
