# -*- coding: utf-8 -*-
r"""lead_three_spots.py — 逐条核对用户指出的三处: 三角块 / 任右侧 / 稳右侧"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D                                   # noqa: E402
import glyph_geometry as G                              # noqa: E402
import tcslib                                           # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'GR_ZH101.iso')
w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128
cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
code2ch = {v: k for k, v in cs['codes'].items()}
T = G.Templates()

rec = [r for f, _x, rs in faces if f == 'large' for r in rs]
rect_of_code = {}
for idx, r in enumerate(rec):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 > u0 and v1 > v0:
        rect_of_code[idx + 0x20] = (u0, v0, u1, v1)


def show(code, note=''):
    r = rect_of_code.get(code)
    if not r:
        print('    code=0x%02X  **没有非空记录** %s' % (code, note))
        return
    u0, v0, u1, v1 = r
    cell = ink[v0:v1, u0:u1]
    ch = code2ch.get(code)
    t = T.get(ch) if ch else None
    iou = ''
    if t is not None and cell.shape == (16, 16):
        inter = int(np.logical_and(cell, t).sum()); uni = int(np.logical_or(cell, t).sum())
        iou = ' 与模板 IoU=%.4f' % (inter / max(1, uni))
    # 右侧 16px 邻域有没有墨
    right = int(ink[v0:v1, min(W - 1, u1):min(W, u1 + 16)].sum())
    print('    code=0x%02X %-4s rec=(%4d,%3d,%4d,%4d) 墨%3d%s  右侧16px内墨 %d %s'
          % (code, ch or '—', u0, v0, u1, v1, int(cell.sum()), iou, right, note))


print('=' * 78)
print('① 用户说的"上下三角块" = y=395 那 4 条记录')
print('=' * 78)
for c in (0x7B, 0x7D, 0xE7, 0xF1):
    show(c, '(0x7B/0x7D 是引擎滚动箭头?)' if c in (0x7B, 0x7D) else '(ç/ñ 拉丁字母)')
print('  这 4 条记录的 rect 并集区域内的全部墨:')
xs = [rect_of_code[c] for c in (0x7B, 0x7D, 0xE7, 0xF1) if c in rect_of_code]
if xs:
    X0 = min(r[0] for r in xs); Y0 = min(r[1] for r in xs)
    X1 = max(r[2] for r in xs); Y1 = max(r[3] for r in xs)
    print('    x%d..%d y%d..%d 墨 %d px' % (X0, X1, Y0, Y1, int(ink[Y0:Y1, X0:X1].sum())))
    print('    **该区域外扩 ±8 内的墨** (可能是残留): %d px'
          % int(ink[max(0, Y0 - 8):Y1 + 8, max(0, X0 - 8):X1 + 8].sum()))

print()
print('=' * 78)
print('② 用户说的"稳 右侧" = 单字节带 0x80..0x9F')
print('=' * 78)
for c in range(0x9C, 0xA0):
    show(c)
u0, v0, u1, v1 = rect_of_code[0x9C]
print('  稳 的 rect 右边界 x=%d; 其后 32px (x=%d..%d, y=%d..%d) 的墨:' % (u1, u1, u1 + 32, v0, v1))
seg = ink[v0:v1, u1:min(W, u1 + 32)]
print('    墨 %d px' % int(seg.sum()))
ys, xs2 = np.nonzero(seg)
if len(ys):
    print('    分布 x=%d..%d y=%d..%d' % (u1 + xs2.min(), u1 + xs2.max(), v0 + ys.min(), v0 + ys.max()))
print('  该区是否被任何 FT 记录覆盖?', end=' ')
cov = [c for c, r in rect_of_code.items() if r[0] <= u1 + 8 and r[2] > u1 and r[1] < v1 and r[3] > v0]
print(cov if cov else '否 ⇒ **纯残留, 可以清**')

print()
print('=' * 78)
print('③ 用户说的"任 右侧"')
print('=' * 78)
for ch in ('任', '人'):
    if ch not in cs['pair_of']:
        print('  %s 不在 charset 里' % ch)
        continue
    b1, b2 = cs['pair_of'][ch]
    slot = tcslib.pair_slot(b1, b2)
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    print('  %s 码=%02X%02X slot=%d row=%d col=%d cell=(%d,%d) 墨=%d'
          % (ch, b1, b2, slot, slot // 62, slot % 62, x, y, int(ink[y:y + 16, x:x + 16].sum())))
    t = T.get(ch)
    cell = ink[y:y + 16, x:x + 16]
    if t is not None:
        inter = int(np.logical_and(cell, t).sum()); uni = int(np.logical_or(cell, t).sum())
        print('     与模板 IoU=%.4f' % (inter / max(1, uni)))
    print('     右侧 16px (x=%d..%d) 墨 %d' % (x + 16, x + 32, int(ink[y:y + 16, x + 16:min(W, x + 32)].sum())))
    print('     该格内墨的 bbox: ', end='')
    yy, xx = np.nonzero(cell)
    print('x+%d..x+%d y+%d..y+%d' % (xx.min(), xx.max(), yy.min(), yy.max()) if len(xx) else '空')
