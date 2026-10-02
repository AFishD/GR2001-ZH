#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""font_res_probe.py - 验证 FONT.RES face 结构 + 渲染带矩形叠加的 atlas
1. hex dump 0x91f..0x99f 与 0x1224 区域(下一个 face 的头)
2. 全文件搜 {x0,y0,x1,y1} 记录运行(y0=h 高度关系: h-y0==26)
3. atlas 前 6 行渲染 + 224 矩形叠加 → font_rects.png
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..'))

import struct
import numpy as np
from PIL import Image, ImageDraw

BASE = os.path.join(REPO_ROOT, 'docs', 'han_v2')
buf = open(BASE + r'\artifacts\font_rsfb_engine.bin', 'rb').read()

def hexdump(a, b):
    for p in range(a, b, 16):
        row = buf[p:p+16]
        print('  %04x: %s  %s' % (p, row.hex(' '), ''.join(
            chr(c) if 32 <= c < 127 else '.' for c in row)))

print('== face1 头 0x2d..0x5f ==')
hexdump(0x2d, 0x5f)
print('== face1 记录尾 → 下一段 0x90f..0x9af ==')
hexdump(0x90f, 0x9af)
print('== 0x121f..0x129f ==')
hexdump(0x121f, 0x129f)
print('== 文件尾 0x1b00..0x1c36 ==')
hexdump(0x1b00, 0x1c36)

# 全文件: 找 h-y0==26 且 x0<x1<=512 的 10B 记录运行
print('\n== h-y0==26 记录运行(全文件) ==')
p = 0
runs = []
cur = None
while p + 10 <= len(buf):
    x0, y0, x1, y1, tag = struct.unpack_from('<5H', buf, p)
    ok = (y1 - y0 == 26 and 0 <= x0 < x1 <= 512 and y1 <= 512 and tag < 0x8000)
    if ok:
        if cur is None:
            cur = p
    else:
        if cur is not None and p - cur >= 40:
            runs.append((cur, p))
        cur = None
    p += 10
if cur is not None and p - cur >= 40:
    runs.append((cur, p))
for a, b in runs:
    n = (b - a) // 10
    ys = set()
    for q in range(a, b, 10):
        x0, y0, x1, y1, tag = struct.unpack_from('<5H', buf, q)
        ys.add((y0, y1))
    print('  0x%x..0x%x  %d 条  (y0,y1)集=%s' % (a, b, n, sorted(ys)))

# 渲染 atlas + 矩形
pak = open(BASE + r'\artifacts\COMMON_PAK.bin', 'rb').read()
atlas = np.frombuffer(pak[0x1069:0x1069 + 512*512], dtype=np.uint8).reshape(512, 512)
S = 2
img = Image.fromarray(255 - atlas[:160]).convert('RGB').resize((512*S, 160*S), Image.NEAREST)
dr = ImageDraw.Draw(img)
for q in range(0x5f, 0x91f, 10):
    x0, y0, x1, y1, tag = struct.unpack_from('<5H', buf, q)
    ch = chr(0x20 + (q - 0x5f)//10)
    dr.rectangle([x0*S, y0*S, x1*S-1, y1*S-1], outline=(255, 0, 0))
    dr.text((x0*S+1, y0*S+1), ch, fill=(0, 120, 255))
img.save(BASE + r'\font_rects.png')
print('\nfont_rects.png 已写出 (红=224 记录矩形, 蓝=字符 0x20+i)')
