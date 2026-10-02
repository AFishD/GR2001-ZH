# -*- coding: utf-8 -*-
"""Probe old 2002 Chinese0-4.rsb (512x512 RGBA4444) layout; render sample sheet."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import struct, os
from PIL import Image, ImageDraw

BASE = os.path.join(REPO_ROOT, 'build', 'bases', 'Ghost Recon')
ART = os.path.join(BASE, 'Data', 'Shell', 'Art')
OUT = os.path.join(REPO_ROOT, 'work', 'tmp', 'pcfont')
cdat = open(os.path.join(BASE, 'Chinese.dat'), 'rb').read().decode('gbk')
print('Chinese.dat chars:', len(cdat))

def load_rsb4444(path, hdr):
    d = open(path, 'rb').read()
    w, h = struct.unpack_from('<II', d, 4)
    px = d[hdr:hdr + w * h * 2]
    img = Image.new('RGBA', (w, h))
    buf = img.load()
    # 4444 LE: byte0 low nibble? try b=lo, g=hi? standard R4444: pixel = a<<12|r<<8|g<<4|b
    data = struct.unpack('<%dH' % (w * h), px)
    for y in range(h):
        row = data[y * w:(y + 1) * w]
        for x in range(w):
            v = row[x]
            r = (v >> 12) & 0xF; g = (v >> 8) & 0xF; b = (v >> 4) & 0xF; a = v & 0xF
            buf[x, y] = (r * 17, g * 17, b * 17, a * 17)
    return img

for n in range(5):
    p = os.path.join(ART, 'Chinese%d.rsb' % n)
    d = open(p, 'rb').read()
    w, h = struct.unpack_from('<II', d, 4)
    print('Chinese%d.rsb: %dx%d hdr=%d' % (n, w, h, 93))
    img = load_rsb4444(p, 93)
    a = img.split()[3]
    gray = Image.composite(Image.new('RGB', img.size, (255, 255, 255)),
                           Image.new('RGB', img.size, (0, 0, 0)), a)
    # try grids
    for cell, cols in [(16, 32), (24, 21), (12, 42), (32, 16)]:
        rows_n = h // cell
        cap = cols * rows_n
        # ink in last row cells
        ink_last = 0
        ink_first = 0
        for i in range(cols):
            cx, cy = i, rows_n - 1
            cnt = 0
            for y in range(cy * cell, (cy + 1) * cell, 2):
                for x in range(cx * cell, (cx + 1) * cell, 2):
                    if gray.getpixel((x, y))[0] > 100:
                        cnt += 1
            ink_last += cnt
        # first 40 cells ink
        for i in range(min(40, cap)):
            cx, cy = i % cols, i // cols
            for y in range(cy * cell, (cy + 1) * cell, 2):
                for x in range(cx * cell, (cx + 1) * cell, 2):
                    if gray.getpixel((x, y))[0] > 100:
                        ink_first += 1
        print('   cell %d grid %dx%d: first40 ink=%d lastrow ink=%d' % (cell, cols, rows_n, ink_first, ink_last))
    if n == 0:
        sheet = Image.new('RGB', (8 * 32, 4 * 48), (210, 210, 220))
        dr = ImageDraw.Draw(sheet)
        for k in range(32):
            cx, cy = k % 32, k // 32
            c = gray.crop((cx * 16, cy * 16, (cx + 1) * 16, (cy + 1) * 16)).resize((32, 32), Image.NEAREST)
            x, y = (k % 8) * 32, (k // 8) * 48
            sheet.paste(c, (x, y))
            dr.text((x + 2, y + 34), '%d%s' % (k, cdat[k]), fill=(0, 0, 120))
        sheet.save(os.path.join(OUT, 'sheet_chinese0_rsb_16px.png'))
        print('   saved sheet_chinese0_rsb_16px.png')
