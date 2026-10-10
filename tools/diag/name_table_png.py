# -*- coding: utf-8 -*-
r"""name_table_png.py — 生成"英文原名 → 中文译名"对照表图片 (会话工具)
用法: python name_table_png.py <out.png> [行数]
"""
import json
import os
import re
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

GR_LBA = 19175
TAB_OFF, TAB_STEP = 0x830, 48
RE_NAME = re.compile(rb'<ActorName>(.*?)</ActorName>', re.S)
CJK = r'C:\Windows\Fonts\msyh.ttc'
MONO = r'C:\Windows\Fonts\consola.ttf'


def scan(iso):
    d = open(iso, 'rb').read()
    base = GR_LBA * 2048
    noff = struct.unpack_from('<I', d, base + 0x10)[0]
    nend = struct.unpack_from('<I', d, base + 4)[0]
    nms = [x.decode('latin-1') for x in d[base + noff:base + nend].split(b'\x00') if x]
    out = []
    for i, nm in enumerate(nms):
        if not nm.upper().endswith('.ATR'):
            continue
        r = struct.unpack_from('<12I', d, base + TAB_OFF + TAB_STEP * i)
        stored, real, off = r[6], r[7], r[8]
        m = RE_NAME.search(d[base + off:base + off + real])
        if not m:
            continue
        out.append((nm, bytes(m.group(1))))
    return out


def main():
    out = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 26
    en = dict(scan('work/builds/GR_EN_ORIG/GR_EN_ORIG.iso'))
    zh = dict(scan('work/builds/GR_ZH77/GR_ZH77.iso'))
    dec = json.load(open('tools/font_pipeline/data/charset_compiled_zh16.json', encoding='utf-8'))
    codes = {v: k for k, v in dec['codes'].items()}
    pairs = {tuple(v): k for k, v in dec['pair_of'].items()}

    def decode(b):
        s, i = [], 0
        b = b.rstrip(b' ')
        while i < len(b):
            if b[i] in codes:
                s.append(codes[b[i]]); i += 1
            elif i + 1 < len(b) and (b[i], b[i + 1]) in pairs:
                s.append(pairs[(b[i], b[i + 1])]); i += 2
            else:
                s.append('?'); i += 1
        return ''.join(s)

    rows = []
    for nm, vb in zh.items():
        va = en.get(nm)
        if va is None or va == vb:
            continue
        if any(c >= 0x80 for c in va):
            continue
        rows.append((nm, va.decode('ascii').rstrip(' '), decode(vb)))
    step = max(1, len(rows) // n)
    sample = rows[::step][:n]

    W, H, rh = 900, 90 + 30 * len(sample), 30
    img = Image.new('RGB', (W, H), (18, 20, 26))
    dr = ImageDraw.Draw(img)
    f_t = ImageFont.truetype(MONO, 18)
    f_m = ImageFont.truetype(MONO, 15)
    f_c = ImageFont.truetype(CJK, 17)
    dr.text((16, 14), 'GR_ZH77  ActorName  EN -> ZH   (%d/%d ATR translated)' % (len(rows), len(zh)),
            font=f_t, fill=(240, 220, 120))
    dr.line([(16, 42), (W - 16, 42)], fill=(90, 95, 110), width=1)
    for i, (nm, e, c) in enumerate(sample):
        y = 52 + i * rh
        dr.text((16, y + 6), '%3d' % (i + 1), font=f_m, fill=(120, 128, 145))
        dr.text((60, y + 6), nm, font=f_m, fill=(150, 200, 255))
        dr.text((330, y + 6), e, font=f_m, fill=(200, 205, 215))
        dr.text((560, y + 4), c, font=f_c, fill=(140, 235, 150))
        dr.line([(16, y + rh - 3), (W - 16, y + rh - 3)], fill=(40, 44, 54), width=1)
    img.save(out)
    print('%s (%dx%d, %d 行样例; 共 %d 条汉化)' % (out, W, H, len(sample), len(rows)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
