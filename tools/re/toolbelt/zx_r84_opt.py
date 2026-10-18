# -*- coding: utf-8 -*-
r"""zx_r84_opt.py — round84：**真实天花板（正确版）**（只读，不写盘）

前两版 solver 有 bug（把"已占格位"当空闲）。本版：
  ① 严格分离「记录占位」与「字形格位」两个集合
  ② 记录可自由平移（任意 x；y 可任意，但记录本身高 16/13）
  ③ 用条带公式把记录装进若干条 16px 带，再在剩余晶格上数 16x16 字形格
  ④ 给出「不动现役 1736 格位」与「整体重铺」两种口径下的最大新字数

产出 work/builds/GR_ZH98/temp/r84/opt.txt
"""
import io
import os
import sys
import json

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np        # noqa: E402
import tcslib             # noqa: E402
import zx_lib             # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r84')
os.makedirs(OUT, exist_ok=True)
W, H = 1024, 512
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH123', 'GR_ZH123.iso')
B = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    B.append(s)


iso = tcslib.Iso(ISO)
names = []
for i in range(2000):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
pak_e = iso.img_entry(tcslib.MENU_LBA, names.index('COMMON.PAK'))
pak = bytes(iso.read(pak_e['iso_off'], pak_e['stored']))
nm, psm, aw, ah, clut, pxs, PX = tcslib.parse_pak_records(pak)[1]
img, cov = zx_lib.decode_engine(pak[PX:PX + pxs], W, H)
ft_e = iso.img_entry(tcslib.MENU_LBA, names.index('FONT.RES'))
exp = b''.join(s[0] for s in tcslib.lzo_subs(bytes(iso.read(ft_e['iso_off'], ft_e['stored']))))
he, faces = tcslib.parse_ft_faces(exp)
iso.close()

uniq = {}
for (fn, fld, rs) in faces:
    for i, r in enumerate(rs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        uniq.setdefault((u0, v0, u1, v1), []).append((fn, i))
live = [r for r in sorted(uniq) if img[r[1]:r[3], r[0]:r[2]].any()]
N_CUR = 1736
P('有墨记录矩形 %d 个（宽 %s）' % (len(live), sorted({r[2] - r[0] for r in live})))
P('现役对偶字形 %d 个' % N_CUR)


def shelf_pack(rects, xmax=W):
    """把矩形按「条带(shelf)」排：每条高度 = 该条内最高者, 宽度累计 <= xmax。
       返回 (条带列表, 总高)。每条 = (y, h, [(x, w, rect)])。"""
    order = sorted(rects, key=lambda r: (-(r[3] - r[1]), -(r[2] - r[0])))
    shelves = []
    for r in order:
        w, h = r[2] - r[0], r[3] - r[1]
        placed = False
        for sh in shelves:
            if sh['h'] >= h and sh['x'] + w <= xmax:
                sh['items'].append((sh['x'], w, r))
                sh['x'] += w
                placed = True
                break
        if not placed:
            shelves.append({'h': h, 'x': w, 'items': [(0, w, r)]})
    y = 0
    for sh in shelves:
        sh['y'] = y
        y += sh['h']
    return shelves, y


P('')
P('=' * 80)
P('① 记录压成「条带」需要多少高度？')
for tag, wf in (('原样（宽 16/10/8）', lambda r: r[2] - r[0]),
                ('全部压到 8px 宽', lambda r: min(r[2] - r[0], 8)),
                ('全部压到 8px 宽 + 高 13', lambda r: min(r[2] - r[0], 8))):
    rs = [(r[0], r[1], r[0] + wf(r), r[1] + (13 if '13' in tag else (r[3] - r[1])))
          for r in live]
    sh, hh = shelf_pack(rs)
    P('   %-28s -> %2d 条带, 总高 %3d px (=%.1f 条 16px 带)'
      % (tag, len(sh), hh, hh / 16.0))

P('')
P('=' * 80)
P('② 记录占掉 B 条 16px 带后，剩下能放几个字形格')


def max_glyphs(rec_h, ncol=62, y0=0):
    """记录占顶部 rec_h 行；余下 (H-rec_h) 行按 y0+16r 排格位。"""
    rows = 0
    r = 0
    while y0 + 16 * r + 16 <= H - rec_h:
        rows += 1
        r += 1
    return rows * ncol, rows


for tag, wf, hf in (('原样', lambda r: r[2] - r[0], lambda r: r[3] - r[1]),
                    ('压到 8px 宽', lambda r: min(r[2] - r[0], 8), lambda r: r[3] - r[1]),
                    ('压到 8x13', lambda r: min(r[2] - r[0], 8), lambda r: min(r[3] - r[1], 13))):
    rs = [(r[0], r[1], r[0] + wf(r), r[1] + hf(r)) for r in live]
    sh, hh = shelf_pack(rs)
    tot, rows = max_glyphs(hh)
    P('   %-12s 记录高 %3d -> 余 %3d 行 × 62 = %4d 个字形格  ⇒ 新字上限 **%d**'
      % (tag, hh, rows, tot, tot - N_CUR))

P('')
P('=' * 80)
P('③ 不动现役格位（现役 1736 在 62列/y0=2/row>=12 加 3 的位置），记录重排')
gb = np.zeros((H, W), bool)
for s in range(N_CUR):
    row, col = divmod(s, 62)
    y = 2 + 16 * (row + (3 if row >= 12 else 0))
    gb[y:y + 16, 16 * col:16 * col + 16] = True
free = ~gb
placed = 0
for r in sorted(live, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1]))):
    w, h = r[2] - r[0], r[3] - r[1]
    got = None
    for y in range(0, H - h + 1):
        ok = ~free[y:y + h].any(axis=0)
        run = 0
        for x in range(W):
            if ok[x]:
                run += 1
                if run >= w:
                    got = (x - w + 1, y)
                    break
            else:
                run = 0
        if got:
            break
    if got:
        free[got[1]:got[1] + h, got[0]:got[0] + w] = False
        placed += 1
P('   记录放置 %d/%d' % (placed, len(live)))
f2 = free.copy()
n = 0
for row in range(32):
    for col in range(62):
        y, x = 16 * row, 16 * col
        if y + 16 <= H and not f2[y:y + 16, x:x + 16].any():
            f2[y:y + 16, x:x + 16] = True
            n += 1
P('   ⇒ 不动现役格位时, 还能放 **%d** 个新字' % n)

with io.open(os.path.join(OUT, 'opt.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'opt.txt'))
