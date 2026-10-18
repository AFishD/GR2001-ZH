# -*- coding: utf-8 -*-
r"""zx_r84_cap.py — round84：**图集容量上限**（只读，不写盘）

问题：h=512、容器尺寸不变、1024x512@4bpp 的 `new_font_revised` 图集里，
     到底最多能塞多少个字形（对偶码格位 + 单字节记录位）？

口径（全部盘上实测）：
  · 对偶格位: slot -> (row,col) ; x = 16*col ; y = y0 + 16*(row + gap if row>=gaprow)
    (ncol, gaprow, gap, y0) 是 cave 里的**代码常量**，本脚本当搜索变量穷举
  · 记录采样窗 = 记录矩形 (u0,v0,u1,v1) 原样（r83 已实证无 +4/+2）
  · 容器只有 1024*512 = 524,288 texel

产出 work/builds/GR_ZH98/temp/r84/cap.txt
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
cont = pak[PX:PX + pxs]
img, cov = zx_lib.decode_engine(cont, W, H)
ft_e = iso.img_entry(tcslib.MENU_LBA, names.index('FONT.RES'))
slot = bytes(iso.read(ft_e['iso_off'], ft_e['stored']))
exp = b''.join(s[0] for s in tcslib.lzo_subs(slot))
he, faces = tcslib.parse_ft_faces(exp)
iso.close()
P('源盘 %s' % os.path.basename(ISO))
P('  容器 %d B ; h=%d ; 图集 %dx%d = %d texel ; 墨 %d'
  % (pxs, ah, W, H, W * H, int(img.sum())))

uniq = {}
for (fn, fld, rs) in faces:
    for i, r in enumerate(rs):
        b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0:
            continue
        uniq.setdefault((u0, v0, u1, v1), []).append((fn, i))
rects = sorted(uniq)
nblank = sum(1 for (u0, v0, u1, v1) in rects if not img[v0:v1, u0:u1].any())
area = sum((u1 - u0) * (v1 - v0) for (u0, v0, u1, v1) in rects)
occ = np.zeros((H, W), bool)
for (u0, v0, u1, v1) in rects:
    occ[v0:v1, u0:u1] = True
P('  非空记录 %d 条 -> 唯一矩形 %d 个（其中全空白 %d 个）'
  % (sum(len(v) for v in uniq.values()), len(rects), nblank))
P('  矩形面积和 %d texel (%.1f 格) ; 并集 %d texel (%.1f 格)'
  % (area, area / 256.0, int(occ.sum()), occ.sum() / 256.0))
widths = {}
for (u0, v0, u1, v1) in rects:
    widths[u1 - u0] = widths.get(u1 - u0, 0) + 1
P('  记录宽度分布 (px: 个数) = %s' % dict(sorted(widths.items())))
heights = {}
for (u0, v0, u1, v1) in rects:
    heights[v1 - v0] = heights.get(v1 - v0, 0) + 1
P('  记录高度分布 (px: 个数) = %s' % dict(sorted(heights.items())))

P('')
P('=' * 76)
P('A) 解析上界（纯面积，与对齐无关）')
P('   图集 %d texel = %d 个 16x16 格' % (W * H, W * H // 256))
cur = 1736 * 256 + int(occ.sum())
P('   现役 1736 对偶格位(%d) + 记录并集(%d) = %d ; 空余 %d texel = %.1f 格'
  % (1736 * 256, int(occ.sum()), cur, W * H - cur, (W * H - cur) / 256.0))
P('   ★ 纯面积允许再加 **%d** 个 16x16 字形' % ((W * H - cur) // 256))


def place_records(free, rects, yalign16=True):
    """把 rects 铺进 free(布尔图, True=空闲)；返回放置表或 None。"""
    placed = {}
    f = free.copy()
    order = sorted(rects, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1])))
    ys = list(range(0, H, 16)) if yalign16 else list(range(H))
    for (u0, v0, u1, v1) in order:
        w, h = u1 - u0, v1 - v0
        got = None
        for y in ys:
            if y + h > H:
                continue
            rowfree = f[y:y + h]
            ok = ~rowfree.any(axis=0)
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
        placed[(u0, v0, u1, v1)] = (x, y)
    return placed, int(f.sum())


P('')
P('=' * 76)
P('B) 几何求解：固定「N 个格位行」的网格，看记录能否挤进剩缝')
rows_out = []
for ncol in (60, 62, 63, 64):
    for gridrows in range(26, 33):
        for (y0, gaprow, gap) in ((2, 12, 3), (2, 12, 2), (2, 12, 0), (0, 12, 0), (0, 99, 0)):
            busy = np.zeros((H, W), bool)
            ok = True
            for row in range(gridrows):
                y = y0 + 16 * (row + (gap if row >= gaprow else 0))
                if y + 16 > H:
                    ok = False
                    break
                for col in range(ncol):
                    x = 16 * col
                    if x + 16 > W:
                        ok = False
                        break
                    busy[y:y + 16, x:x + 16] = True
                if not ok:
                    break
            if not ok:
                continue
            nslots = gridrows * ncol
            r = place_records(~busy, rects)
            if r is None:
                rows_out.append((nslots, ncol, gridrows, y0, gap, '✗记录放不下', 0))
                continue
            _, left = r
            newcells = left // 256
            rows_out.append((nslots, ncol, gridrows, y0, gap, '✓', newcells))
rows_out.sort(reverse=True)
P('  ncol  rows y0 gap | 格位 | 记录 | 剩余 texel | 还能加')
for (nslots, ncol, gridrows, y0, gap, tag, newcells) in rows_out[:24]:
    P('   %2d   %2d   %d  +%d | %4d | %s | %7d | %d'
      % (ncol, gridrows, y0, gap, nslots, tag, newcells * 256, newcells))
P('')
if rows_out and rows_out[0][5] == '✓':
    b = rows_out[0]
    P('  ★★ 本轮几何上限 = 网格 %d 格位（ncol=%d, rows=%d, y0=%d, gap=+%d）, '
      '记录全部塞下后还能再放 %d 个新字' % (b[0], b[1], b[2], b[3], b[4], b[6]))

with io.open(os.path.join(OUT, 'cap.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'cap.txt'))
