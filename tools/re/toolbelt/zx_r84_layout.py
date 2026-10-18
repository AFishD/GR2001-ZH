# -*- coding: utf-8 -*-
r"""zx_r84_layout.py — round84：**可实现的图集布局求解器**（只读，不写盘）

关键约束（前几版 solver 都没建模对）：
  ① 对偶槽号 slot 是**一维**的，位置 (x,y) 由 cave 的公式唯一决定：
        row = slot // ncol          col = slot % ncol
        x   = 16*col                y  = y0 + 16*(row + (gap if row>=gaprow else 0))
     ⇒ 字形格位的 y **只能**是 {y0 + 16k}；x **只能**是 16c。
  ② 因此「哪些 band 放字形、哪些放记录」一旦确定，可容纳的字形数就定了。
  ③ 记录矩形可自由平移（任意 x/y），但要装进剩下的 band 里。

做法：枚举 (n_glyph_bands, 记录 band 的分配)，用 shelf packing 判断记录是否装得下，
      输出可容纳的**对偶字形数**上限。
产出 work/builds/GR_ZH98/temp/r84/layout.txt
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
ascii_r = [r for r in live if any(i < 96 for i in uniq[r])]
han_r = [r for r in live if any(i >= 96 for i in uniq[r])]
P('有墨记录 %d（ASCII 段 %d / 汉字段 %d）; 宽度分布 %s'
  % (len(live), len(ascii_r), len(han_r), sorted({r[2] - r[0] for r in live})))
P('现役对偶字形 1736')


def shelf_h(rs, xmax=W):
    """条带化需要的高度（每条高度 = 条内最高）。"""
    order = sorted(rs, key=lambda r: (-(r[3] - r[1]), -(r[2] - r[0])))
    shelves = []
    for r in order:
        w, h = r[2] - r[0], r[3] - r[1]
        for sh in shelves:
            if sh[0] >= h and sh[1] + w <= xmax:
                sh[1] += w
                break
        else:
            shelves.append([h, w])
    return sum(sh[0] for sh in shelves), len(shelves)


P('')
P('① 记录条带化需要多少高度')
for tag, rs in (('全部 204 条', live), ('ASCII 段（8px 宽）', ascii_r), ('汉字段（16px 宽）', han_r)):
    hh, ns = shelf_h(rs)
    P('   %-22s -> %d 条带, 高 %d px (=%.1f 个 16px band)' % (tag, ns, hh, hh / 16.0))

P('')
P('=' * 80)
P('② 枚举：n_glyph_bands 个 band 给字形（每 band 62 格），其余 band 给记录')
P('   band 总数上限 = floor((512 - y0) / 16)')
for y0 in (0, 2):
    nband = (H - y0) // 16
    P('   y0=%d -> %d 个 band' % (y0, nband))
    best = None
    for ng in range(20, nband + 1):
        # 剩下的 band 拼成一块连续区域（记录可自由放）
        free_rows = nband - ng
        free_px = free_rows * 16 - y0
        if free_px <= 0:
            continue
        hh, ns = shelf_h(live, xmax=W)
        ok = hh <= free_px
        glyphs = ng * 62
        if ok:
            if best is None or glyphs > best[0]:
                best = (glyphs, ng, free_rows, free_px, hh)
    if best:
        P('     ★ 字形 band %d 个 -> 可容纳 %d 个对偶字形 ; 留 %d 个 band (%d px) 给记录'
          % (best[1], best[0], best[2], best[3]))
        P('       记录需要 %d px 高 ; 新增上限 = %d − 1736 = **%d**'
          % (best[4], best[0], best[0] - 1736))
    else:
        P('     （无解）')

P('')
P('=' * 80)
P('③ 更细的分配：记录按「最小高度」占固定条带（48px = 3 band），字形用其余 band')
nband = (H - 2) // 16
P('   y0=2, band 总数 %d' % nband)
for rec_bands in (3, 4):
    gb = nband - rec_bands
    P('   记录占 %d band -> 字形 %d band -> %d 个对偶字形 ; 新增上限 %d'
      % (rec_bands, gb, gb * 62, gb * 62 - 1736))

P('')
P('=' * 80)
P('④ 结论')
P('   记录最紧需要 48 px = 3 个 16px band （不改记录宽度）')
P('   图集 512 px，y=2 起步 ⇒ %d 个 band' % nband)
P('   ⇒ 字形最多 %d 个 band × 62 = %d 个对偶字形' % (nband - 3, (nband - 3) * 62))
P('   ⇒ 相对现役 1736，**本轮新增上限 = %d**' % ((nband - 3) * 62 - 1736))

with io.open(os.path.join(OUT, 'layout.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'layout.txt'))
