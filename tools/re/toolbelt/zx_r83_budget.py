# -*- coding: utf-8 -*-
r"""zx_r83_budget.py — round83：h=512 图集容量预算（只读，不写盘）

场景对比（全部按"引擎口径"像素 + 记录采样窗实测）:
  S0  基线: NCOL=62, 现役 slot 0..1503, 记录不动
  S1  加 row 25/26/27 (slot 0..1735) 但**不搬带** (带被压 = 冲突)
  S2  NCOL=64, row 0..27 (slot 0..1791)
  S3  基线 + 记录窗也全部搬开
产出 work/builds/GR_ZH98/temp/r83/budget.txt
"""
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np     # noqa: E402
import tcslib          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MENU_LBA = tcslib.MENU_LBA
W, H = 1024, 512
DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV
B = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s)
    B.append(s)


iso = tcslib.Iso(ISO)
names = []
for i in range(2000):
    e = iso.img_entry(MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
ft_e = iso.img_entry(MENU_LBA, names.index('FONT.RES'))
slot = bytes(iso.read(ft_e['iso_off'], ft_e['stored']))
exp = b''.join(s[0] for s in tcslib.lzo_subs(slot))
he, faces = tcslib.parse_ft_faces(exp)
iso.close()

# 记录采样窗 busy
rec = np.zeros((H, W), dtype=bool)
uniq = set()
for (nm, fld, rs) in faces:
    for r in rs:
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        uniq.add((u0, v0, u1, v1))
        x0, y0 = max(0, u0 + DU), max(0, v0 + DV)
        x1, y1 = min(W, u1 + DU), min(H, v1 + DV)
        if x1 > x0 and y1 > y0:
            rec[y0:y1, x0:x1] = True
P('记录: 非空 544 条, 唯一矩形 %d 个, 采样窗并集 %d texel (%.1f 个 16x16 格)'
  % (len(uniq), int(rec.sum()), rec.sum() / 256.0))

# 16x16 记录(整格宽) 与 8x16 (ASCII) 分开统计
n16 = sum(1 for (a, b, c, d) in uniq if c - a == 16 and d - b == 16)
n8 = sum(1 for (a, b, c, d) in uniq if c - a == 8)
P('   其中 16x16 矩形 %d 个 ; 8 宽矩形 %d 个 ; 其它 %d 个'
  % (n16, n8, len(uniq) - n16 - n8))


def grid_busy(ncol, nrow_max, n_slots):
    """引擎格位 busy 图。x = 16*(slot%ncol), y = 2 + 16*(row + 3 if row>=12)."""
    g = np.zeros((H, W), dtype=bool)
    off = 0
    for s in range(n_slots):
        row, col = s // ncol, s % ncol
        if row > nrow_max:
            break
        x = 16 * col
        y = 2 + 16 * (row + (3 if row >= 12 else 0))
        y2 = min(H, y + 16)
        if y2 > y and x + 16 <= W:
            g[y:y2, x:x + 16] = True
        else:
            off += 1
    return g, off


def pack_max(busy, label):
    """贪心: 光栅序铺 16x16 (也试列序), 返回可放个数。"""
    best = 0
    bestsp = None
    for mode in ('row', 'col'):
        b = busy.copy()
        cnt = 0
        spots = []
        rng = ([(y, x) for y in range(H - 15) for x in range(W - 15)] if mode == 'row'
               else [(y, x) for x in range(W - 15) for y in range(H - 15)])
        for (y, x) in rng:
            if not b[y:y + 16, x:x + 16].any():
                b[y:y + 16, x:x + 16] = True
                cnt += 1
                spots.append((x, y))
        if cnt > best:
            best, bestsp = cnt, spots
        P('   [%s/%s] 贪心可铺 %d 个 16x16' % (label, mode, cnt))
    return best, bestsp


for (ncol, nrow, nslots, tagname) in ((62, 24, 1504, 'S0 基线 NCOL=62 只用 row0..24'),
                                      (62, 27, 1736, 'S1 NCOL=62 row0..27 (与 EN/KB 带冲突)'),
                                      (64, 31, 2048, 'S2 NCOL=64 row0..31 (理论上限)'),
                                      (64, 27, 1792, 'S3 NCOL=64 row0..27')):
    g, off = grid_busy(ncol, nrow, nslots)
    used = g | rec
    free = ~used
    P('')
    P('=' * 70)
    P('%s : 格位 %d 个 (越界 %d) ; 格位面积 %d ; 并集 %d ; 自由 %d texel = %.1f 格'
      % (tagname, min(nslots, (nrow + 1) * ncol), off, int(g.sum()), int(used.sum()),
         int(free.sum()), free.sum() / 256.0))
    # 自由区里 16 对齐的整格数
    n_align = 0
    for m in range(H // 16):
        for k in range(W // 16):
            if not used[16 * m:16 * m + 16, 16 * k:16 * k + 16].any():
                n_align += 1
    P('   16 对齐的完全空闲格 = %d' % n_align)
    for (nm, fld, rs) in faces:
        if nm != 'default':
            continue
        need = 0
        for r in rs:
            b0, b1, u0, v0, u1, v1 = r
            if u1 <= u0:
                continue
            if used[max(0, v0 + DV):v1 + DV, max(0, u0 + DU):u1 + DU].any():
                pass
    if ncol == 62 and nrow == 24:
        best, spots = pack_max(used, tagname)
        P('   ★ 自由区最多可再放 %d 个 16x16 字形' % best)
        # 记录窗(212 条)能否塞进这些位置 —— 只要个数够即可
        P('   ⇒ 记录窗占 %d texel (等效 %.1f 格), 剩余理论容量 %.1f 格'
          % (int(rec.sum()), rec.sum() / 256.0, (free.sum()) / 256.0))

P('')
P('=' * 70)
P('★ 结论性上限（与实现无关的几何上限）')
P('   1024x512 图集 = 2048 个 16x16 格')
P('   现役 544 条记录的采样窗 = %d texel = %.1f 格' % (int(rec.sum()), rec.sum() / 256.0))
P('   ⇒ 理论可用字形格 ≈ 2048 - %.1f = %.1f  (但格位公式 x=16*col,col<62|64 且 y=2+16*row\')'
  % (rec.sum() / 256.0, 2048 - rec.sum() / 256.0))

with open(os.path.join(OUT, 'budget.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'budget.txt'))
