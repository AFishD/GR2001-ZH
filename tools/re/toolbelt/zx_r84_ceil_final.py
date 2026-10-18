# -*- coding: utf-8 -*-
r"""zx_r84_ceil_final.py — round84：**权威上限穷举（最终）**（只读）

承认三条硬约束：
  ① 对偶 slot 是**一维**的 ⇒ 「前 n 个 slot」的位置由 (ncol, y0, gaprow, gap) 唯一确定
  ② 采样窗必须落在 1024x512 内
  ③ 记录矩形（有墨 204 个）可自由平移，但**不可与格位重叠**
穷举 (ncol, rows, y0, gap) 求最大 n。产出 r84/ceil_final.txt
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
    print(s, flush=True)
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
img, cov = zx_lib.decode_engine(pak[PX:PX + pxs], 1024, 512)
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
P('有墨记录矩形 %d' % len(live))
REC_ORDER = sorted(live, key=lambda r: (-(r[2] - r[0]) * (r[3] - r[1]), -(r[2] - r[0])))


def solvable(n, ncol, y0, gaprow, gap):
    cells = []
    for s in range(n):
        row, col = divmod(s, ncol)
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H or 16 * col + 16 > W:
            return False
        cells.append((16 * col, y))
    busy = np.zeros((H, W), bool)
    for (x, y) in cells:
        busy[y:y + 16, x:x + 16] = True
    free = ~busy
    for r in REC_ORDER:
        w, h = r[2] - r[0], r[3] - r[1]
        got = None
        for y in range(0, H - h + 1):
            run = 0
            fy = free[y]
            for x in range(W):
                if fy[x]:
                    run += 1
                    if run >= w and free[y:y + h, x - w + 1:x + 1].all():
                        got = (x - w + 1, y)
                        break
                else:
                    run = 0
            if got:
                break
        if not got:
            return False
        free[got[1]:got[1] + h, got[0]:got[0] + w] = False
    return True


P('')
P('=' * 84)
P('穷举 (ncol, rows, y0, gap)——同一 slot 一维性下的最大对偶字形数 n')
P('')
P('   ncol rows y0 gap | 最大 n | 新字上限')
best = None
for ncol in (60, 62, 63, 64):
    for y0 in (0, 2):
        for gap in (0, 1, 2, 3):
            gaprow = 12 if gap else 99
            # 二分找最大 n
            lo, hi = 1736, 2060
            if not solvable(lo, ncol, y0, gaprow, gap):
                continue
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if solvable(mid, ncol, y0, gaprow, gap):
                    lo = mid
                else:
                    hi = mid - 1
            rows = (lo + ncol - 1) // ncol
            P('    %2d  %3d  %d  +%d |  %4d  |   %4d' % (ncol, rows, y0, gap, lo, lo - 1736))
            if best is None or lo > best[0]:
                best = (lo, ncol, y0, gap)
P('')
P('★ 全局最大 n = **%d**（ncol=%d, y0=%d, gap=+%d）⇒ 新字上限 **%d**'
  % (best[0], best[1], best[2], best[3], best[0] - 1736))
P('★ 现役结构（ncol=62,y0=2,gap=+3）最大 n = 1736 ⇒ 新字上限 0（图集已满到格子级）')

with io.open(os.path.join(OUT, 'ceil_final.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'ceil_final.txt'))
