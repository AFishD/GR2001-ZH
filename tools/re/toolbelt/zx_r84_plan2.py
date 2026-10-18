# -*- coding: utf-8 -*-
r"""zx_r84_plan2.py — round84：**可达布局求解（修正版）**（只读，不写盘）

上一版 `zx_r84_plan.py` 的 count_new 会把"已占的现役格位"当成空闲（先标记再计数）；
本版严格分两步：**先把现役字形占位标记好 → 再在剩余空间里数新字**。

S1 保守：现役 1736 格位 + 现役记录**都不动** → 只在空处放新字（最易实现）
S2 现役格位不动，记录允许整体重排（16 行对齐）
S3 gap→0：网格 ncol=62 × 32 行 = 1984 槽，现役 1736 重铺（记录先占 2 条带）
产出 work/builds/GR_ZH98/temp/r84/plan2.txt
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
allr = sorted(uniq)
live = [r for r in allr if img[r[1]:r[3], r[0]:r[2]].any()]
P('唯一记录矩形 %d（有墨 %d）' % (len(allr), len(live)))
N_CUR = 1736


def grid_cells(ncol, rows, y0, gaprow=99, gap=0, n=N_CUR):
    """返回现役 n 个格位占用的单元格集合 [(x,y)]（只取前 n 个 slot）。"""
    out = []
    for s in range(n):
        row, col = divmod(s, ncol)
        if row >= rows:
            break
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        x = 16 * col
        if y + 16 > H or x + 16 > W:
            continue
        out.append((x, y))
    return out


def mask_of(cells):
    m = np.zeros((H, W), bool)
    for (x, y) in cells:
        m[y:y + 16, x:x + 16] = True
    return m


def pack_records(free):
    f = free.copy()
    for (u0, v0, u1, v1) in sorted(live, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1]))):
        w, h = u1 - u0, v1 - v0
        got = None
        for y in range(0, H - h + 1, 16):
            ok = ~f[y:y + h].any(axis=0)
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
        x, y = got
        f[y:y + h, x:x + w] = False
    return f


def count_new(occ):
    """occ = 已占用图; 在 (16c,16r) 晶格上贪心放 16x16，返回可放个数与落点。"""
    f = occ.copy()
    n = 0
    spots = []
    for row in range(32):
        for col in range(62):
            y, x = 16 * row, 16 * col
            if y + 16 <= H and x + 16 <= W and not f[y:y + 16, x:x + 16].any():
                f[y:y + 16, x:x + 16] = True
                n += 1
                spots.append((x, y))
    return n, spots


P('')
P('=' * 80)
P('S1 保守：现役格位（62列, y0=2, row>=12 加 3）+ 现役记录坐标 【都不动】')
cell1 = grid_cells(62, 28, 2, 12, 3)
occ = mask_of(cell1)
P('   现役格位 %d 个 -> 占 %d texel' % (len(cell1), int(occ.sum())))
for r in allr:
    occ[r[1]:r[3], r[0]:r[2]] = True
n1, sp1 = count_new(occ)
P('   ⇒ 还能放 **%d** 个新字 ; 剩余自由 %d texel = %.1f 格' % (n1, int((~occ).sum()), (~occ).sum() / 256.0))
ys1 = sorted({y for (x, y) in sp1})
P('   落点 y 带 = %s' % ys1)

P('')
P('=' * 80)
P('S2 现役格位【不动】，记录允许整体重排（16 行对齐）')
fr = pack_records(~mask_of(cell1))
if fr is None:
    P('   记录重排失败')
else:
    occ2 = mask_of(cell1) | (~fr)
    n2, sp2 = count_new(occ2)
    P('   ⇒ 记录重排后可放 **%d** 个新字' % n2)
    P('   （注：记录重排必然占用现役格位之外的区域，新字只在剩余晶格空位里放）')

P('')
P('=' * 80)
P('S3 gap→0：网格 ncol=62 × R 行（槽 62R），现役 1736 前 n 个槽占位, 记录先占条带')
for rows in (30, 31, 32):
    for y0 in (0, 2):
        cells = grid_cells(62, rows, y0, 99, 0)
        if len(cells) < N_CUR:
            P('   rows=%d y0=%d: 只能放 %d 个现役格位（<1736）— 跳过' % (rows, y0, len(cells)))
            continue
        gmask = mask_of(cells[:N_CUR])
        fr2 = pack_records(~gmask)
        if fr2 is None:
            P('   rows=%d y0=%d: 记录放不下' % (rows, y0))
            continue
        occ3 = gmask | (~fr2)
        n3, sp3 = count_new(occ3)
        P('   rows=%2d y0=%d 槽 %4d: 现役 1736 重铺后还能放 **%4d** 个新字 ⇒ 总字形 %d'
          % (rows, y0, rows * 62, n3, N_CUR + n3))

P('')
P('=' * 80)
P('★ 对照')
P('   现役占格（实测）: 对偶 1736 + ASCII 段 47 + 汉字段 106 = 1889 / 2048')
P('   面积硬上界（零浪费、记录全压到 8px）= %d' % (2048 - 47 - 54 - 1736))
P('   364 需要 364 ⇒ 远超任何上界')

with io.open(os.path.join(OUT, 'plan2.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'plan2.txt'))
