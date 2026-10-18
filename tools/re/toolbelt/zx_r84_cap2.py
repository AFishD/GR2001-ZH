# -*- coding: utf-8 -*-
r"""zx_r84_cap2.py — round84：**364 是否可行的判定**（只读，不写盘）

在 cap.py 的基础上把问题问死：
  「在 1024x512 的图集里，**除记录外**最多能有多少个 16x16 字形格？」

做法：
  ① 面积硬上界（与几何无关）
  ② 对若干网格参数，用「记录优先 + 字形填充」的求解器反推字形格位上限
  ③ 对记录做「采样窗可缩小」的敏感性分析（16x16 -> 8x16 / 14x16 / 8x13）

产出 work/builds/GR_ZH98/temp/r84/cap2.txt
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

uniq = {}
for (fn, fld, rs) in faces:
    for i, r in enumerate(rs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        uniq.setdefault((u0, v0, u1, v1), []).append((fn, i))
rects = sorted(uniq)
P('源盘 GR_ZH123 ; 唯一记录矩形 %d ; 现役对偶格位 1736 ; 图集 %dx%d' % (len(rects), W, H))

# ── ① 面积硬上界 ──
P('')
P('=' * 76)
P('① 面积硬上界（与对齐/寻址无关）')
tot = W * H
P('   图集总 texel              = %d' % tot)
P('   现役 1736 个对偶格位       = %d texel' % (1736 * 256))
for tag, shrinkf in (('记录保持原样', lambda w, h: (w, h)),
                     ('记录缩到 8x16', lambda w, h: (min(w, 8), min(h, 16))),
                     ('记录缩到 8x13', lambda w, h: (min(w, 8), min(h, 13)))):
    a = 0
    occm = np.zeros((H, W), bool)
    for (u0, v0, u1, v1) in rects:
        w, h = shrinkf(u1 - u0, v1 - v0)
        a += w * h
    usable = tot - a
    P('   %-14s : 记录 %6d texel -> 可给字形 %d texel = **%d** 个 16x16 格'
      % (tag, a, usable, usable // 256))
    P('        ⇒ 相对现役 1736 还能再加 **%d** 个' % (usable // 256 - 1736))

# ── ② 记录优先 + 字形填充求解 ──
def pack(free, rects, w_limit=None):
    f = free.copy()
    out = {}
    order = sorted(rects, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1])))
    for (u0, v0, u1, v1) in order:
        w, h = u1 - u0, v1 - v0
        got = None
        for y in list(range(0, H, 16)) + list(range(H)):
            if y + h > H:
                continue
            row = f[y:y + h]
            ok = ~row.any(axis=0)
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
        out[(u0, v0, u1, v1)] = (x, y)
    return out, f


def count_glyph_cells(free_after_rec):
    """剩余自由区里能放多少个 16x16 格（按 16 对齐 + 16 行网格，贪心）"""
    b = free_after_rec.copy()
    n = 0
    cells = []
    for y in range(0, H - 15, 16):
        for x in range(0, W - 15, 16):
            if not b[y:y + 16, x:x + 16].any():
                b[y:y + 16, x:x + 16] = True
                n += 1
                cells.append((x, y))
    return n, cells


P('')
P('=' * 76)
P('② 求解：「先把 208 个记录铺好，再数剩下能放多少 16x16 格」')
empty = np.ones((H, W), bool)
r0 = pack(empty, rects)
if r0 is None:
    P('   记录无法铺进空图集（不应该）')
else:
    _, left = r0
    n, cells = count_glyph_cells(left)
    P('   记录优先铺满后：剩 %d texel ; 可放 **%d** 个 16x16 格' % (int(left.sum()), n))
    P('   ⇒ 加上 1736 现役 = 上限 **%d** 个对偶字形' % (1736 + n))
    # 记录占用 y 范围
    ys = sorted({y for (x, y) in r0.values()})
    P('   记录落点 y 值 = %s' % ys)
    P('   字形格落点 y 值(前 40) = %s' % sorted({y for (x, y) in cells})[:40])

P('')
P('=' * 76)
P('③ 结论')
P('   364 个新字 = 364 * 256 = %d texel' % (364 * 256))
P('   现役 1736 已占 %d texel ; 图集只有 %d texel' % (1736 * 256, tot))
P('   ⇒ 「1736 + 364 = 2100 个对偶字形」= %d texel ; 图集 %d texel ; 差 %d texel'
  % (2100 * 256, tot, 2100 * 256 - tot))
P('   ⇒ 即便记录**完全不占空间**，图集也放不下 2100 个 16x16 字形（硬上界 %d 个）' % (tot // 256))

with io.open(os.path.join(OUT, 'cap2.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'cap2.txt'))
