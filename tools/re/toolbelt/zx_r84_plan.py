# -*- coding: utf-8 -*-
r"""zx_r84_plan.py — round84：**具体可达布局求解**（只读，不写盘）

问题：在 h=512 / 容器不变 / 图集 1024x512 的前提下，
      **最多再塞几个新字**？（要求布局可实现，不是面积估算）

模型：
  · 记录矩形（有墨 204 个）可整体重排，但必须落在 16 行对齐的条带上
  · 对偶格位必须落在 (16c, 16r) 晶格上
  · 新字一律走对偶格位
算法：
  S1「保守」：现役 1736 格位 + 现役记录**都不动**，只在空处放新字（最容易实现）
  S2「重排记录」：现役 1736 格位不动，记录允许整体重排到任意 16 行对齐位置
  S3「gap→0 + 记录重排」：网格改成 ncol=62 / 32 行 / 无 gap（槽位 1922，需重铺 744 个现役字形）
产出 work/builds/GR_ZH98/temp/r84/plan.txt
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
cs = json.load(io.open(tcslib.CHARSET, encoding='utf-8'))
recs = {f[0]: f[2] for f in faces}

uniq = {}
for (fn, fld, rs) in faces:
    for i, r in enumerate(rs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        uniq.setdefault((u0, v0, u1, v1), []).append((fn, i))
allr = sorted(uniq)
live = [r for r in allr if img[r[1]:r[3], r[0]:r[2]].any()]     # 204
P('唯一记录矩形 %d（有墨 %d）' % (len(allr), len(live)))
P('ASCII 段(idx0..95) 有墨矩形 %d ; 汉字段(idx>=96) 有墨矩形 %d'
  % (sum(1 for r in live if any(i < 96 for (f, i) in uniq[r])),
     sum(1 for r in live if any(i >= 96 for (f, i) in uniq[r]))))


def grid_busy(ncol, rows, y0=0, gaprow=99, gap=0):
    b = np.zeros((H, W), bool)
    for row in range(rows):
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H:
            return None
        for col in range(ncol):
            x = 16 * col
            if x + 16 > W:
                return None
            b[y:y + 16, x:x + 16] = True
    return b


def pack_records(free, yalign=16):
    f = free.copy()
    for (u0, v0, u1, v1) in sorted(live, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1]))):
        w, h = u1 - u0, v1 - v0
        got = None
        for y in range(0, H - h + 1, yalign):
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


def count_new(free):
    """在 free 上按晶格光栅序放 16x16，返回可放个数。"""
    f = free.copy()
    n = 0
    for row in range(32):
        for col in range(62):
            y, x = 16 * row, 16 * col
            if y + 16 <= H and x + 16 <= W and not f[y:y + 16, x:x + 16].any():
                f[y:y + 16, x:x + 16] = True
                n += 1
    return n


P('')
P('=' * 78)
P('S1 保守：现役 1736 格位 + 现役记录坐标**都不动**')
cur = np.zeros((H, W), bool)
for s in range(1736):
    row, col = divmod(s, 62)
    cur[16 * (row + (3 if row >= 12 else 0)) + 0:16 * (row + (3 if row >= 12 else 0)) + 16,
        16 * col:16 * col + 16] = True
for r in allr:
    cur[r[1]:r[3], r[0]:r[2]] = True
n1 = count_new(~cur)
P('   ⇒ 还能放 **%d** 个新字（不动任何现役像素；剩余 %d texel）' % (n1, int((~cur).sum())))

P('')
P('=' * 78)
P('S2 只重排记录（现役 1736 格位不动）')
gb = grid_busy(62, 28, y0=2, gaprow=12, gap=3)   # 现役的 28 行结构
fr = pack_records(~gb)
if fr is None:
    P('   记录重排失败')
else:
    n2 = count_new(fr)
    P('   ⇒ 记录重排后可放 **%d** 个新字（视作现役格位占满 0..1735 的前提）' % n2)

P('')
P('=' * 78)
P('S3 gap→0：网格 62 列 × 32 行 = 1984 槽（现役 1736 必须重铺）')
for rows in (31, 32):
    gb = grid_busy(62, rows, y0=0, gaprow=99, gap=0)
    fr = pack_records(~gb)
    if fr is None:
        P('   rows=%d: 记录放不下' % rows)
        continue
    n3 = count_new(fr)
    P('   rows=%d (槽 %d): 记录重排后可放 **%d** 个新字（含现役 1736 ⇒ 总 %d）'
      % (rows, rows * 62, n3, 1736 + n3))

P('')
P('=' * 78)
P('★ 实测结论（现役 1504+232=1736 已占图集 1889/2048 格位）')
P('   S1 保守不动           = %d' % n1)
P('   面积硬上界（零浪费）  = %d' % (2048 - 47 - 106 - 1736))
P('   364 需要              = 364  ⇒ **差 %d 个**（%.0f%% 的缺口）'
  % (364 - (2048 - 47 - 106 - 1736), 100.0 * (364 - (2048 - 47 - 106 - 1736)) / 364.0))

with io.open(os.path.join(OUT, 'plan.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'plan.txt'))
