# -*- coding: utf-8 -*-
r"""zx_r84_solve2.py — round84：**权威布局求解（修正重叠 bug）**（只读）

★ 关键修正：上一版 solver 把「记录」放在**已占的格位上**也算成功（`occ` 没当障碍），
  导致 n=1984 的假可行。本版严格：
    ① 字形格位是**硬障碍**（记录绝不可重叠）
    ② 记录可自由平移，但必须落在真正空闲的 texel 上
    ③ 采样窗必须落在 1024x512 内
    ④ 失败即 None（不会"勉强大致放一下"）

产出 work/builds/GR_ZH98/temp/r84/solve2.txt + solve2.json
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
live = [r for r in sorted(uniq) if img[r[1]:r[3], r[0]:r[2]].any()]   # 只有有墨的需要地方
P('有墨记录矩形 %d（空白 4 个可共用一块）' % len(live))
P('矩形尺寸: %s' % sorted({(r[2] - r[0], r[3] - r[1]) for r in live}))


def obstacles_from_cells(cells):
    m = np.zeros((H, W), bool)
    for (x, y) in cells:
        m[y:y + 16, x:x + 16] = True
    return m


def place_records(occ):
    """occ = 硬障碍（字形格位）。返回 (放置表, 剩余空闲图) 或 None。"""
    free = ~occ
    placed = {}
    for r in sorted(live, key=lambda r: (-(r[2] - r[0]) * (r[3] - r[1]), -(r[2] - r[0]))):
        w, h = r[2] - r[0], r[3] - r[1]
        got = None
        for y in range(0, H - h + 1):
            colfree = ~free[y:y + h].any(axis=0)
            run = 0
            for x in range(W):
                if colfree[x]:
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
        free[y:y + h, x:x + w] = False
        placed[r] = (x, y)
    return placed, free


def glyph_cells(n, ncol, y0, gaprow, gap):
    out = []
    for s in range(n):
        row, col = divmod(s, ncol)
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H:
            return None
        out.append((16 * col, y))
    return out


def solve(n, ncol, y0, gaprow, gap):
    cells = glyph_cells(n, ncol, y0, gaprow, gap)
    if cells is None or len(cells) != n:
        return None
    r = place_records(obstacles_from_cells(cells))
    if r is None:
        return None
    placed, free = r
    return cells, placed, int(free.sum())


P('')
P('=' * 84)
P('★ 权威求解（字形格位 = 硬障碍；记录仅可放在真正空闲 texel 上）')
P('')
P('   ncol gap y0 | 最大 n | 新字 | 剩余 texel | 说明')
CFG = ((62, 2, 12, 3, '现役结构（不动现役字形）'),
       (62, 2, 12, 2, '去掉 1 条 16px 带'),
       (62, 2, 12, 1, '去掉 2 条 16px 带'),
       (62, 2, 99, 0, 'gap→0, y0=2'),
       (62, 0, 99, 0, '★ gap→0 + y0=0'),
       (63, 0, 99, 0, 'ncol=63（需改 cave）'),
       (64, 0, 99, 0, 'ncol=64（右边缘风险）'))
best_all = {}
for (ncol, y0, gaprow, gap, tag) in CFG:
    b, bl = None, None
    for n in range(1736, 2050):
        r = solve(n, ncol, y0, gaprow, gap)
        if r is None:
            break
        b, bl = n, r[2]
    P('   %2d  +%d  %d |  %4d  | %4d | %8d   | %s' % (ncol, gap, y0, b, b - 1736, bl, tag))
    best_all[(ncol, y0, gap)] = (b, bl)

P('')
P('=' * 84)
P('★ 选定方案: ncol=62, gap=+0, y0=0')
NCOL, Y0, GAPROW, GAP = 62, 0, 99, 0
N_MAX, LEFT = best_all[(NCOL, Y0, GAP)]
P('   最大对偶字形 n = **%d** ⇒ 新字 **%d** ; 剩余 %d texel (%.1f 格位)'
  % (N_MAX, N_MAX - 1736, LEFT, LEFT / 256.0))
cells, placed, left = solve(N_MAX, NCOL, Y0, GAPROW, GAP)
ys = sorted({y for (x, y) in cells})
P('   字形 y 带 %d 个: %d..%d' % (len(ys), ys[0], ys[-1]))
byy = {}
for k, v in placed.items():
    byy.setdefault(v[1], []).append((v[0], k))
P('   记录落点（按 y）:')
for y in sorted(byy):
    xs = sorted(x for x, k in byy[y])
    P('     y=%3d : %2d 条, x=%d..%d, 宽 %s'
      % (y, len(xs), xs[0], xs[-1], sorted({k[2] - k[0] for x, k in byy[y]})))

# ── 输出供补丁使用的布局 ──
lay = dict(ncol=NCOL, y0=Y0, gap=GAP, n_max=N_MAX, n_new=N_MAX - 1736, left=LEFT,
           cells=[[s, x, y] for s, (x, y) in enumerate(cells)],
           recs={'%d,%d,%d,%d' % k: list(v) for k, v in placed.items()})
with io.open(os.path.join(OUT, 'solve2.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(lay, f, ensure_ascii=False, indent=1)
P('')
P('★ cave 需要的常量改动:')
P('   · 0x4170E8  addiu $t5,$t5,3  ->  addiu $t5,$t5,0    (gap 3→0)')
P('   · 0x4170F8  addiu $t5,$t6,2  ->  addiu $t5,$t6,0    (V0 = 16*row + 0)')
P('   · 0x4170FC  addiu $t6,$t6,18 ->  addiu $t6,$t6,16   (V1 = 16*row + 16)')
P('   · ncol 62 / stride 16 / gap 判定 slt 12 均不变')
P('[out] %s' % os.path.join(OUT, 'solve2.json'))
with io.open(os.path.join(OUT, 'solve2.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('[out] %s' % os.path.join(OUT, 'solve2.txt'))
