# -*- coding: utf-8 -*-
r"""zx_r84_final.py — round84：**权威布局求解器**（只读，不写盘）

★ 这一版把前面所有版本的建模错误都修掉了：
  ① 对偶格位位置由 cave 公式唯一决定（slot 是**一维**的）：
        row=slot//62, col=slot%62, x=16*col, y=2+16*(row + (3 if row>=12 else 0))
     本脚本把 (gaprow, gap, y0) 当变量，但**承认 slot 一维性**：
     给定「前 n 个 slot 放字形」，它们的位置就唯一确定了。
  ② 记录矩形可自由平移（任意 x/y），装进剩余空间。
  ③ 硬约束：任何采样窗必须落在 1024x512 内（V1 <= 512）。

目标：求 **最大 n**（= 1736 + 新字），使「n 个字形格位 + 204 个有墨记录矩形」可共存。
产出 work/builds/GR_ZH98/temp/r84/final.txt
"""
import io
import os
import sys

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
rec = faces[1][2]
uniq = {}
for i, r in enumerate(rec):
    b0, b1, u0, v0, u1, v1 = r
    if u1 <= u0:
        continue
    uniq.setdefault((u0, v0, u1, v1), []).append(i)
live = [r for r in sorted(uniq) if img[r[1]:r[3], r[0]:r[2]].any()]
P('有墨记录矩形 %d ; 宽 %s' % (len(live), sorted({r[2] - r[0] for r in live})))


def glyph_cells(n, ncol=62, y0=2, gaprow=12, gap=3):
    out = []
    for s in range(n):
        row, col = divmod(s, ncol)
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H:
            return None
        out.append((16 * col, y))
    return out


def try_layout(n, **kw):
    cells = glyph_cells(n, **kw)
    if cells is None:
        return None
    busy = np.zeros((H, W), bool)
    for (x, y) in cells:
        busy[y:y + 16, x:x + 16] = True
    free = ~busy
    # 记录：大而宽优先；扫所有 y（不限于 16 对齐）
    for (u0, v0, u1, v1) in sorted(live, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1]))):
        w, h = u1 - u0, v1 - v0
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
        if not got:
            return None
    return int((~busy).sum())


P('')
P('=' * 80)
P('★ gap=+3（现役行结构，不动现役字形位置）下，最大 n = 1736 + 新字')
best = None
for n in range(1736, 2100):
    r = try_layout(n, ncol=62, y0=2, gaprow=12, gap=3)
    if r is None:
        P('   n=%d ... 记录放不下（上限在前一个）' % n)
        break
    best = n
P('   ⇒ 最大 n = **%d** ⇒ 新字上限 = **%d**' % (best, best - 1736))

P('')
P('=' * 80)
P('★ gap=+0（去掉 3 行空档，现役字形需重铺）')
for (y0, gaprow, gap) in ((2, 99, 0), (0, 99, 0)):
    b2 = None
    for n in range(1736, 2100):
        r = try_layout(n, ncol=62, y0=y0, gaprow=gaprow, gap=gap)
        if r is None:
            break
        b2 = n
    P('   y0=%d gap=0 ⇒ 最大 n = **%d** ⇒ 新字上限 = **%d**' % (y0, b2, b2 - 1736))

P('')
P('=' * 80)
P('★ gap=+2（只去掉 1 条 16px 带）')
for (y0, gap) in ((2, 2), (2, 1)):
    b3 = None
    for n in range(1736, 2100):
        r = try_layout(n, ncol=62, y0=y0, gaprow=12, gap=gap)
        if r is None:
            break
        b3 = n
    P('   y0=%d gap=+%d ⇒ 最大 n = **%d** ⇒ 新字上限 = **%d**' % (y0, gap, b3, b3 - 1736))

P('')
P('=' * 80)
P('★ ncol=63 / 64（需要改 cave，且右边缘可能被 REPEAT 采样）')
for ncol in (63, 64):
    for (y0, gap) in ((2, 0), (0, 0), (2, 3)):
        b4 = None
        for n in range(1736, 2100):
            r = try_layout(n, ncol=ncol, y0=y0, gaprow=12 if gap else 99, gap=gap)
            if r is None:
                break
            b4 = n
        P('   ncol=%d y0=%d gap=+%d ⇒ 最大 n = **%d** ⇒ 新字上限 = **%d**'
          % (ncol, y0, gap, b4, b4 - 1736))

with io.open(os.path.join(OUT, 'final.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'final.txt'))
