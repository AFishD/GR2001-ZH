# -*- coding: utf-8 -*-
"""r51 探针: 现役盘 GR_ZH98 的 FT 记录矩形长什么样 / ASCII 带在哪 / 单字节码怎么放。只读。"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib
import dump_font

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
font = dump_font.load_font(ISO)
faces = font['faces']
atlas = font['atlas']
print('atlas %dx%d psm=0x%02X px_size=0x%X' % (atlas['w'], atlas['h'], atlas['psm'], atlas['px_size']))
for fi, (nm, fld, recs) in enumerate(faces):
    print('face %d %-8s fld=%s nrec=%d' % (fi, nm, fld, len(recs)))

gray = dump_font.atlas_gray(atlas, view='engine')
ink = (np.frombuffer(gray, np.uint8).reshape(atlas['h'], atlas['w']) == 0)
print('ink texels =', int(ink.sum()))

nm, fld, recs = faces[tcslib.FONT_FACE_DEFAULT]
print('--- default face 记录矩形分类 ---')
sizes = {}
for idx, r in enumerate(recs):
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    k = (u1 - u0, v1 - v0)
    sizes.setdefault(k, []).append(idx + 0x20)
for k in sorted(sizes):
    v = sizes[k]
    print('  %2dx%-3d  %4d 条  首批码: %s' % (k[0], k[1], len(v),
                                          ' '.join('%02X' % c for c in v[:10])))

print('--- ASCII 0x21..0x7E 记录 ---')
for c in (0x21, 0x28, 0x49, 0x57, 0x6D, 0x7A, 0x3F):
    r = recs[c - 0x20]
    print('  %r code=%02X rec=(%d,%d,%d,%d) adv=%d' % (chr(c), c, r[2], r[3], r[4], r[5], r[1]))
    sub = ink[r[3]:r[5], r[2]:r[4]]
    print('     盘上墨点=%d' % int(sub.sum()))
