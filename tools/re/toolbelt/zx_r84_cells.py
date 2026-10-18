# -*- coding: utf-8 -*-
r"""zx_r84_cells.py — round84：**图集格位需求核算**（只读）

问题：把「现役全部字形 + 364 个新字」全部放进 1024x512 图集，需要多少个 16x16 **格位**？
      图集一共只有 2048 个格位。缺口是多少？

口径：
  · 对偶码       -> 1 个 16x16 格位/字
  · 单字节记录   -> 记录矩形（8 宽的两条可以共用一个格位）
  · 空白记录     -> 不占位（可全部指向同一块空白）
产出 work/builds/GR_ZH98/temp/r84/cells.txt
"""
import io
import os
import sys
import json
import csv

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
R82 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
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

# ── 唯一记录矩形 + 是否有墨 ──
uniq = {}
for (fn, fld, rs) in faces:
    for i, r in enumerate(rs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        uniq.setdefault((u0, v0, u1, v1), []).append((fn, i))
rects = sorted(uniq)
live = [r for r in rects if img[r[1]:r[3], r[0]:r[2]].any()]
blank = [r for r in rects if r not in live]
P('图集 %dx%d = %d texel = %d 个 16x16 格位' % (W, H, W * H, W * H // 256))
P('唯一记录矩形 %d（有墨 %d / 全空白 %d）' % (len(rects), len(live), len(blank)))

# ── 记录需要的格位数：把「有墨」矩形按宽度装进 16x16 格 ──
def cells_for(rs):
    """每条 16x16 格可容纳: 2 个宽度<=8 的矩形, 或 1 个更宽的。"""
    narrow = [r for r in rs if r[2] - r[0] <= 8]
    wide = [r for r in rs if r[2] - r[0] > 8]
    return len(wide) + (len(narrow) + 1) // 2, len(narrow), len(wide)


n_rec_cells, n_narrow, n_wide = cells_for(live)
P('记录占格位: 窄(<=(8px)) %d 个 -> %d 格 ; 宽 %d 个 -> %d 格 ; 合计 **%d** 格'
  % (n_narrow, (n_narrow + 1) // 2, n_wide, n_wide, n_rec_cells))
P('  （空白记录可全部指向同一块 1 格空白，已省）')

# ── charset 现状 ──
CH = tcslib.CHARSET
cs = json.load(io.open(CH, encoding='utf-8'))
n_codes = len(cs['codes'])
n_pair = len(cs['pair_of'])
P('')
P('charset: codes(单字节码) = %d ; pair_of(对偶码) = %d' % (n_codes, n_pair))

miss = []
with io.open(os.path.join(R82, 'rich_missing_chars.csv'), encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        miss.append(r['char'])
P('r82 缺字清单 = %d 种' % len(miss))

P('')
P('=' * 76)
P('★ 格位需求核算')
P('  ① 现役对偶字形        = %d 格位' % 1736)
P('  ② 现役单字节记录字形  = %d 格位（%d 条有墨记录）' % (n_rec_cells, len(live)))
P('     —— 其中 %d 条是 ASCII/窄字形（8px），与 ① 里被搬成对偶的 键/练/用 等无重叠' % n_narrow)
P('  ③ 364 个新字          = 364 格位（若全部走对偶码）')
P('  ------------------------------------------------')
need = 1736 + n_rec_cells + 364
P('  合计需要              = 1736 + %d + 364 = **%d 格位**' % (n_rec_cells, need))
P('  图集只有              = **%d 格位**' % (W * H // 256))
P('  ★★ 缺口              = **%d 格位** (%.1f%%)'
  % (need - W * H // 256, 100.0 * (need - W * H // 256) / (W * H // 256)))
P('')
P('  ⇒ 即使把图集排得**一点缝都没有**，也放不下 %d 个字形。' % need)
P('  ⇒ 硬上限 = %d 个字形；扣掉记录 %d 格 ⇒ **最多 %d 个「字形占用格」**'
  % (W * H // 256, n_rec_cells, W * H // 256 - n_rec_cells))
P('  ⇒ 相对现役 1736，**最多再加 %d 个新字**（且要求记录/布局零浪费）'
  % (W * H // 256 - n_rec_cells - 1736))
P('  ⇒ 相对现役 1736，**最多再加 %d 个新字**（若把 %d 条记录缩成 8px 宽，记录只占 %d 格）'
  % (W * H // 256 - (len(rs) and 0 or 0) - 0, 0, 0) if False else '')

# 敏感度：记录缩窄
n2 = len(live)
P('')
P('  敏感度分析（记录矩形宽度处理方式 -> 记录占格 -> 可加新字上限）:')
for tag, f in (('保持原样（8px 的成对共格）', None),
               ('全部记录压到 8px 宽（成对共格）', None),
               ('全部记录压到 8px 宽且用 8px 网格（4 格/格位）', None)):
    if tag.startswith('保持'):
        c = n_rec_cells
    elif tag.startswith('全部记录压到 8px 宽（'):
        c = (n2 + 1) // 2
    else:
        c = (n2 + 3) // 4
    P('     %-38s -> %3d 格 -> 可加 %d 个新字' % (tag, c, 2048 - c - 1736))

with io.open(os.path.join(OUT, 'cells.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'cells.txt'))
