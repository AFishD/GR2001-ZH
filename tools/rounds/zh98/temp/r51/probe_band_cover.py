# -*- coding: utf-8 -*-
"""r51 探针⑨: 底部带 (y>=470) 的**全部采样窗**清单 —— 写补丁前必须确认那里只有这 28 个记录窗。只读。"""
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
am = font['atlas']
faces = font['faces']
cs = tcslib.Charset()
H, W = am['h'], am['w']

print('=== 三个 face 里, 与 y>=470 相交的 FT 记录 ===')
seen = set()
for fi, (nm, fld, recs) in enumerate(faces):
    for idx, (b0, b1, u0, v0, u1, v1) in enumerate(recs):
        if u1 <= u0 or v1 <= v0 or v1 <= 470:
            continue
        code = idx + 0x20
        key = (u0, v0, u1, v1)
        seen.add((fi, code, key))
        ch = cs.codes.get(code)
        print('  face%d %-8s code 0x%02X %-3s rec=(%3d,%3d,%3d,%3d)  字符=%s'
              % (fi, nm, code, ('%r' % ch) if ch else '-', u0, v0, u1, v1, ch or '-'))

print()
print('=== 覆盖掩码: 这些窗覆盖了哪些像素 (y>=470) ===')
cover = np.zeros((H, W), bool)
for (nm, _fld, recs) in faces:
    for (b0, b1, u0, v0, u1, v1) in recs:
        if u1 > u0 and v1 > v0:
            cover[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True
for (_b1, _b2) in cs.enc_pair.values():
    if not (tcslib.PAIR_LEAD_LO <= _b1 < tcslib.PAIR_LEAD_HI):
        continue
    x, y = tcslib.atlas_cell_xy_engine_view(tcslib.pair_slot(_b1, _b2))
    cover[max(0, y):min(H, y + 16), max(0, x):min(W, x + 16)] = True
eng_g = dump_font.atlas_gray(am, view='engine')
eng = (np.frombuffer(eng_g, np.uint8).reshape(H, W) == 0)
band = np.zeros((H, W), bool)
band[470:, :] = True
print('  y>=470 有墨的像素: %d' % int((eng & band).sum()))
print('  y>=470 有墨但**不属于任何采样窗** (=残墨): %d' % int((eng & band & ~cover).sum()))
print('  全图有墨但不属于任何采样窗 (=残墨): %d' % int((eng & ~cover).sum()))
rows = np.where((eng & band & ~cover).any(axis=1))[0]
print('  残墨所在行: %s' % (rows.tolist()[:20] if len(rows) else '无'))

print()
print('=== 28 个目标格 (code 0x80..0x9C 除 0x92) 的现状 ===')
recs = [x for x in faces if x[0] == 'default'][0][2]
tot = 0
for c in sorted(cs.codes):
    if not (0x80 <= c <= 0x9C) or c == 0x92:
        continue
    r = recs[c - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    sub = eng[v0:v1, u0:u1]
    cov = cover[v0:v1, u0:u1]
    tot += int(sub.sum())
    if not cov.all():
        print('  !! %02X 记录窗里有 %d 个像素**不被自己覆盖** (被别的窗压着?)'
              % (c, int((~cov).sum())))
print('  28 个窗现共有墨 %d 点 (全都要被正确字形覆盖)' % tot)

print()
print('=== 28 个旧的"错位字形"位置 (要清理的孤儿行) ===')
for c in (0x80, 0x8B, 0x8C, 0x9C):
    r = recs[c - 0x20]
    u0, v0 = r[2], r[3]
    if c <= 0x8B:
        fx, fy = u0 + 256, 481
    else:
        fx, fy = u0 - 192, 483
    ys = np.arange(fy, fy + 16)
    xs = np.arange(fx, fx + 16)
    orph = [(int(y), int(x)) for y in ys for x in xs if eng[y, x] and not cover[y, x]]
    print('  %02X 旧位置 (%d,%d)..(%d,%d): 墨 %d, 其中**孤儿** %d'
          % (c, fx, fy, fx + 15, fy + 15, int(eng[fy:fy + 16, fx:fx + 16].sum()), len(orph)))
