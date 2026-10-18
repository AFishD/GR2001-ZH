# -*- coding: utf-8 -*-
r"""zx_r83_plan.py — round83 目标布局规划 + 空间普查（只读）

目标布局（**h 保持 512 · 容器尺寸不变 · PAK 不变 · MENU 不变**）：
  · 对偶码槽 = 自然槽号，网格公式 NCOL=62, y = 2 + 16*(row + 3 if row>=12)
    → 可寻址槽 0..1735（row 0..27），现役 1504 个（row 0..24）**一格不动**
  · 新字占槽 1504..1735（232 个格）
  · 记录带 (452,468) EN 与 (482,498) KB 与 row 25/26/27 冲突 ⇒ 必须搬家
    → 在"自由区"里贪心重新排布（8x16 两枚并一个 16x16 格）
产出 work/builds/GR_ZH98/temp/r83/plan.txt
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
import zx_lib          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
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
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'].startswith('?'):
        break
    names.append(e['name'])
ft_e = iso.img_entry(tcslib.MENU_LBA, names.index('FONT.RES'))
slot = bytes(iso.read(ft_e['iso_off'], ft_e['stored']))
exp = b''.join(s[0] for s in tcslib.lzo_subs(slot))
iso.close()
faces, endp = zx_lib.ft_records(exp, 28)
P('FONT.RES 展开 %d B ; 记录区结束 0x%X ; faces %s'
  % (len(exp), endp, [(f[0], f[1][4] * f[1][5]) for f in faces]))

# ── 记录分类 ──
BANDS = {(452, 468): 'EN', (482, 498): 'KB'}
recs = []                     # (face, idx, b0,b1,u0,v0,u1,v1)
for (fn, fld, rows) in faces:
    for i, (off, r) in enumerate(rows):
        recs.append((fn, i, off) + tuple(r))
P('记录总数 %d ; 非空 %d' % (len(recs), sum(1 for r in recs if r[7] > r[5])))
for band, tag in BANDS.items():
    hit = [r for r in recs if (r[6], r[8]) == band and r[7] > r[5]]
    us = sorted({(r[5], r[7]) for r in hit})
    P('  %s 带 v=%s : %d 条 ; 唯一 u 段 %d 个 ; u 范围 %d..%d'
      % (tag, band, len(hit), len(us), us[0][0], us[-1][1]))
    P('      u 起点 %s' % [u for u, _ in us])

# ── 目标布局 busy ──
busy = np.zeros((H, W), dtype=bool)
for s in range(1736):                                   # 槽 0..1735
    row, col = s // 62, s % 62
    x, y = 16 * col, 2 + 16 * (row + (3 if row >= 12 else 0))
    busy[y:y + 16, x:x + 16] = True
NEWCELL = {}
for s in range(1504, 1736):
    row, col = s // 62, s % 62
    NEWCELL[s] = (16 * col, 2 + 16 * (row + (3 if row >= 12 else 0)))
P('目标网格: 槽 0..1735 ; 新槽 1504..1735 = %d 个' % len(NEWCELL))
P('  新槽格子 y 范围 = %d..%d' % (min(v[1] for v in NEWCELL.values()),
                                   max(v[1] for v in NEWCELL.values()) + 16))

# 保留原位的记录（除两条带）
keep = 0
for r in recs:
    fn, i, off, b0, b1, u0, v0, u1, v1 = r
    if u1 <= u0:
        continue
    if (v0, v1) in BANDS:
        continue
    x0, y0 = max(0, u0 + DU), max(0, v0 + DV)
    x1, y1 = min(W, u1 + DU), min(H, v1 + DV)
    busy[y0:y1, x0:x1] = True
    keep += 1
P('留在原位的记录窗 %d 条' % keep)
free0 = ~busy
P('加完网格(0..1735)+原位记录窗后 自由 = %d texel = %.1f 格'
  % (int(free0.sum()), free0.sum() / 256.0))

# ── 给要搬家的带找位置 ──
def place(need_w, need_h, busy, y_lo=DV, x_lo=DU):
    """贪心找采样窗左上角 (x, y)（x>=DU, y>=DV，保证 u0/v0 不为负）。"""
    for y in range(y_lo, H - need_h + 1):
        for x in range(x_lo, W - need_w + 1):
            if not busy[y:y + need_h, x:x + need_w].any():
                return x, y
    return None


moves = []                    # (tag, old_u0, old_v0, old_u1, old_v1, new_u0, new_v0, new_u1, new_v1)
for band in ((452, 468), (482, 498)):
    tag = BANDS[band]
    us = sorted({(r[5], r[7]) for r in recs if (r[6], r[8]) == band and r[7] > r[5]})
    w = us[0][1] - us[0][0]
    h = band[1] - band[0]
    P('-- %s 带: %d 个唯一矩形 (记录 %dx%d, 采样窗 %dx%d) --' % (tag, len(us), w, h, w, h))
    ok = 0
    for k, (u0, u1) in enumerate(us):
        win_w, win_h = u1 - u0, band[1] - band[0]
        pos = place(win_w, win_h, busy)
        if pos is None:
            P('   ✗ 放不下第 %d 个' % k)
            break
        x, y = pos
        busy[y:y + win_h, x:x + win_w] = True
        moves.append((tag, u0, band[0], u1, band[1],
                      x - DU, y - DV, x - DU + win_w, y - DV + win_h))
        ok += 1
    P('   已放置 %d / %d ; 之后自由 = %d texel' % (ok, len(us), int((~busy).sum())))

P('')
P('搬家后自由 = %d texel = %.1f 格 ; 其中 16 对齐空整格 = %d'
  % (int((~busy).sum()), (~busy).sum() / 256.0,
     sum(1 for m in range(32) for k in range(64)
         if not busy[16 * m:16 * m + 16, 16 * k:16 * k + 16].any())))
P('★ 结论: 目标布局在 %d texel 自由空间里为 %d 条带记录找到了新位置'
  % (int((~busy).sum()), len(moves)))

with open(os.path.join(OUT, 'plan.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'plan.txt'))
