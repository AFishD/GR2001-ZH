# -*- coding: utf-8 -*-
r"""zx_r84_solve3.py — round84：**权威布局求解（最终版）**（只读）

★ 修掉的 bug：前几版用「整块 y..y+h 全空的列」当判据，但那一整块里只要有字形就永远失败，
  于是把记录塞到已占位置还报成功。本版对每一行独立扫描。

产出 work/builds/GR_ZH98/temp/r84/solve3.txt + solve3.json
"""
import io
import json
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
P('有墨记录矩形 %d ; 尺寸 %s' % (len(live), sorted({(r[2] - r[0], r[3] - r[1]) for r in live})))


def place(free, rects):
    """free = 可写布尔图（True=空闲）。逐行扫描放矩形。"""
    placed = {}
    for r in sorted(rects, key=lambda r: (-(r[2] - r[0]) * (r[3] - r[1]), -(r[2] - r[0]))):
        w, h = r[2] - r[0], r[3] - r[1]
        got = None
        for y in range(0, H - h + 1):
            run = 0
            for x in range(W):
                if free[y, x]:
                    run += 1
                    if run >= w:
                        # 检查整块
                        if free[y:y + h, x - w + 1:x + 1].all():
                            got = (x - w + 1, y)
                            break
                        run = 0
                else:
                    run = 0
            if got:
                break
        if not got:
            return None
        x, y = got
        free[y:y + h, x:x + w] = False
        placed[r] = (x, y)
    return placed


def solve(n, ncol, y0, gaprow, gap):
    cells = []
    for s in range(n):
        row, col = divmod(s, ncol)
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H:
            return None
        cells.append((16 * col, y))
    if len(set(cells)) != n:
        return None
    occ = np.zeros((H, W), bool)
    for (x, y) in cells:
        occ[y:y + 16, x:x + 16] = True
    placed = place(~occ, live)
    if placed is None:
        return None
    return cells, placed


P('')
P('=' * 86)
P('★ 权威求解（记录逐行扫描、字形格位为硬障碍）')
P('')
P('   ncol gap y0 | 最大 n | 新字上限 | 说明')
res = {}
for (ncol, y0, gaprow, gap, tag) in ((62, 2, 12, 3, '现役结构（不动现役字形）'),
                                     (62, 2, 12, 2, '去掉 1 条 16px 带'),
                                     (62, 2, 12, 1, '去掉 2 条 16px 带'),
                                     (62, 2, 99, 0, 'gap→0, y0=2'),
                                     (62, 0, 99, 0, '★ gap→0 + y0=0'),
                                     (63, 0, 99, 0, 'ncol=63（需改 cave 2 处）'),
                                     (64, 0, 99, 0, 'ncol=64（右边缘 REPEAT 风险）')):
    b = None
    for n in range(1736, 2060):
        if solve(n, ncol, y0, gaprow, gap) is None:
            break
        b = n
    res[(ncol, y0, gap)] = b
    P('   %2d  +%d  %d |  %4d  |   %4d   | %s' % (ncol, gap, y0, b, b - 1736, tag))

P('')
P('=' * 86)
P('★ 与「面积上界」对照')
P('   面积上界（记录并集 40,664 texel，零浪费）= (524288-40664)/256 = %d' % ((W * H - 40664) // 256))
P('   地址/格位综合上界（ncol=62, y0=0, gap=0）= %d' % res[(62, 0, 0)])

NCOL, Y0, GAPROW, GAP = 62, 0, 99, 0
N_MAX = res[(NCOL, Y0, GAP)]
cells, placed = solve(N_MAX, NCOL, Y0, GAPROW, GAP)
P('')
P('★ 选定: ncol=%d y0=%d gap=+%d ⇒ n=%d, 新字 **%d**' % (NCOL, Y0, GAP, N_MAX, N_MAX - 1736))
ys = sorted({y for (x, y) in cells})
P('   字形 y 带 %d 个: %d..%d' % (len(ys), ys[0], ys[-1]))
byy = {}
for k, v in placed.items():
    byy.setdefault(v[1], []).append((v[0], k))
P('   记录落点:')
for y in sorted(byy):
    xs = sorted(x for x, k in byy[y])
    P('     y=%3d : %2d 条, x=%s, 宽 %s' % (y, len(xs), xs[:6], sorted({k[2] - k[0] for x, k in byy[y]})))

lay = dict(ncol=NCOL, y0=Y0, gap=GAP, n_max=N_MAX, n_new=N_MAX - 1736,
           cells=[[s, x, y] for s, (x, y) in enumerate(cells)],
           recs={'%d,%d,%d,%d' % k: list(v) for k, v in placed.items()})
with io.open(os.path.join(OUT, 'solve3.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(lay, f, ensure_ascii=False, indent=1)
P('')
P('★ cave 常量改动:')
P('   · 0x4170E8 addiu $t5,$t5,3  -> +0   (gap 3→0)')
P('   · 0x4170F8 addiu $t5,$t6,2  -> +0   (V0 16*row+0)')
P('   · 0x4170FC addiu $t6,$t6,18 -> +16  (V1 16*row+16)')
P('[out] %s' % os.path.join(OUT, 'solve3.json'))
with io.open(os.path.join(OUT, 'solve3.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('[out] %s' % os.path.join(OUT, 'solve3.txt'))
