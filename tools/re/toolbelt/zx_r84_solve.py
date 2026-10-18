# -*- coding: utf-8 -*-
r"""zx_r84_solve.py — round84：**权威布局求解 + 布局导出**（只读，不写盘）

前几版 solver 的 bug 全部修掉后（承认 slot 一维性 + 记录可自由平移）的权威数字：
     gap=+3 (现役)                         -> 1736 满, 新字 0
     gap=+2                                -> 1798, 新字  62
     gap=+1                                -> 1860, 新字 124
     gap=+0, y0=2                          -> 1922, 新字 186
     gap=+0, y0=0                          -> 1984, 新字 248   ★ 本方案
     ncol=64, gap=+0, y0=0                 -> 2048, 新字 312   (需改 cave+右边缘风险)

本脚本对选定参数**导出完整布局**（每个 slot 的物理位置 + 每个记录的物理位置），
供 zx_r84_patch.py 使用。产出 work/builds/GR_ZH98/temp/r84/solve.json
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
live = sorted(uniq)


def solve(n, ncol=62, y0=0, gaprow=99, gap=0):
    """返回 (slot->(x,y), rect->(x,y), 剩余) 或 None。"""
    cells = []
    for s in range(n):
        row, col = divmod(s, ncol)
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H:
            return None
        cells.append((16 * col, y))
    busy = np.zeros((H, W), bool)
    for (x, y) in cells:
        busy[y:y + 16, x:x + 16] = True
    free = ~busy
    placed = {}
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
        if not got:
            return None
        x, y = got
        free[y:y + h, x:x + w] = False
        placed[r] = (x, y)
    return cells, placed, int((~busy).sum())


P('=' * 80)
P('★ 权威求解（承认 slot 一维性 + 记录自由平移，采样窗必须落在 1024x512 内）')
P('')
P('  ncol gap  y0 | 最大 n | 新字上限 | 说明')
for (ncol, y0, gaprow, gap, tag) in (
        (62, 2, 12, 3, '现役结构（不动现役字形）'),
        (62, 2, 12, 2, '去掉 1 条 16px 带'),
        (62, 2, 12, 1, '去掉 2 条 16px 带'),
        (62, 2, 99, 0, 'gap→0'),
        (62, 0, 99, 0, '★ gap→0 + y0=0（本方案）'),
        (63, 0, 99, 0, 'ncol=63（需改 cave 2 处）'),
        (64, 0, 99, 0, 'ncol=64（需改 cave，右边缘风险）')):
    b = None
    for n in range(1736, 2100):
        if solve(n, ncol=ncol, y0=y0, gaprow=gaprow, gap=gap) is None:
            break
        b = n
    P('   %2d  +%d   %d  |  %4d  |   %4d   | %s' % (ncol, gap, y0, b, b - 1736, tag))

P('')
P('=' * 80)
NCOL, Y0, GAPROW, GAP = 62, 0, 99, 0
N_MAX = None
for n in range(1736, 2100):
    if solve(n, ncol=NCOL, y0=Y0, gaprow=GAPROW, gap=GAP) is None:
        break
    N_MAX = n
P('★ 选定：ncol=%d y0=%d gap=+%d ⇒ 最大对偶字形 n = **%d** ⇒ 新字 **%d**'
  % (NCOL, Y0, GAP, N_MAX, N_MAX - 1736))
cells, placed, left = solve(N_MAX, ncol=NCOL, y0=Y0, gaprow=GAPROW, gap=GAP)
P('   剩余自由 %d texel = %.1f 格位' % (left, left / 256.0))
ys = sorted({y for (x, y) in cells})
P('   字形格位 y 带 = %d 个: %d..%d' % (len(ys), ys[0], ys[-1]))
rys = sorted({y for (x, y) in placed.values()})
P('   记录落点 y = %s' % rys)
P('   记录落点 x 段 = %s' % sorted({x for (x, y) in placed.values()})[:12])

# ── slot 地址公式参数（供 cave 补丁） ──
P('')
P('★ cave 需要的新常量:')
P('   addiu $t6,$zero,NCOL      : 62  (不变)')
P('   addiu $t7,$zero,16        : 16  (不变)')
P('   addiu $t7,$zero,12 / slt  : 行的 gap 判定 —— 本方案 gap=0 ⇒ 让 slt 恒真或把 +3 改成 +0')
P('   addiu $t5,$t5,3 (0x4170E8): 改成 addiu $t5,$t5,0  (gap 3→0)')
P('   addiu $t5,$t6,2  (0x4170F8): V0 = 16*row + 2  -> 2 不变')
P('   addiu $t6,$t6,18 (0x4170FC): V1 = 16*row + 18 -> 18 不变')
P('   ★ y0=0 的实现: 公式是 y = 2 + 16*row, 要得到 y = 0 + 16*row, 需把 "2" 改成 "0"')
P('     对应指令 0x4170F8 addiu $t5,$t6,2 -> 立即数 2 改 0; 同时 0x4170FC 的 18 改 16')

res = dict(ncol=NCOL, y0=Y0, gap=GAP, n_max=N_MAX, n_new=N_MAX - 1736,
           cells=[[s, x, y] for s, (x, y) in enumerate(cells)],
           recs={','.join(map(str, k)): list(v) for k, v in placed.items()},
           left=left)
with io.open(os.path.join(OUT, 'solve.json'), 'w', encoding='utf-8', newline='\n') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
P('')
P('[out] %s' % os.path.join(OUT, 'solve.json'))
with io.open(os.path.join(OUT, 'solve.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('[out] %s' % os.path.join(OUT, 'solve.txt'))
