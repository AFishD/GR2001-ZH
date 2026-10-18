# -*- coding: utf-8 -*-
r"""zx_r84_ceiling.py — round84：**图集真实天花板**（只读，不写盘）

把「1024x512 图集到底还能再放几个 16x16 字形」用**确定性的下界算法**算死：
  ① 现役占用（对偶格位 + 记录采样窗）从盘上实测
  ② 记录允许整体重排（16 行对齐），格位必须在 (16c, 16r) 晶格上
  ③ 用「记录优先 + 格位光栅贪心」求最大可加格位数
  ④ 再给一个更容易实现的上界（记录不动, 只用空缝）

产出 work/builds/GR_ZH98/temp/r84/ceiling.txt
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
liveR = [r for r in rects if img[r[1]:r[3], r[0]:r[2]].any()]
blankR = [r for r in rects if r not in liveR]
P('唯一记录矩形 %d（有墨 %d / 空白 %d）' % (len(rects), len(liveR), len(blankR)))


def grid_busy(ncol, gridrows, y0, gaprow=99, gap=0):
    b = np.zeros((H, W), bool)
    cells = []
    for row in range(gridrows):
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        if y + 16 > H:
            return None, None
        for col in range(ncol):
            x = 16 * col
            if x + 16 > W:
                return None, None
            b[y:y + 16, x:x + 16] = True
            cells.append((x, y))
    return b, cells


def pack_records(free):
    """记录（有墨）优先铺进 free；16 行对齐。返回 (放置表, free')。"""
    f = free.copy()
    out = {}
    # 空白记录全部指向同一小块（用记录自己的尺寸，放在一个角落）
    for (u0, v0, u1, v1) in sorted(liveR, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1]))):
        w, h = u1 - u0, v1 - v0
        got = None
        for y in range(0, H - h + 1, 16):
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


P('')
P('=' * 78)
P('① 记录不动（保持现役坐标），只数「格位晶格上还有多少空位」')
cur = np.zeros((H, W), bool)
for s in range(1736):
    row, col = divmod(s, 62)
    x, y = 16 * col, 16 * (row + (3 if row >= 12 else 0))
    cur[y:y + 16, x:x + 16] = True
for r in rects:
    cur[r[1]:r[3], r[0]:r[2]] = True
free = ~cur
cnt = 0
spots = []
for row in range(32):
    for col in range(62):
        y, x = 16 * row, 16 * col
        if y + 16 <= H and not free[y:y + 16, x:x + 16].any():
            free[y:y + 16, x:x + 16] = True
            cnt += 1
            spots.append((x, y))
P('   记录不动: 现役占用后, 晶格上还能放 **%d** 个 16x16（剩余 %d texel）'
  % (cnt, int((~cur).sum())))
P('   落点 y 分布 = %s' % sorted({y for (x, y) in spots}))

P('')
P('=' * 78)
P('② 记录可整体重排（16 行对齐）+ 格位晶格 —— 求最大可加格位')
res = []
for ncol in (62, 63, 64):
    for y0 in (0, 2):
        for gap in (0, 2, 3):
            gaprow = 12 if gap else 99
            for gridrows in range(26, 33):
                gb, cells = grid_busy(ncol, gridrows, y0, gaprow, gap)
                if gb is None:
                    continue
                r = pack_records(~gb)
                if r is None:
                    continue
                _, freer = r
                # 数晶格上还剩多少
                n = 0
                for row in range(32):
                    for col in range(62):
                        y, x = 16 * row, 16 * col
                        if y + 16 <= H and not freer[y:y + 16, x:x + 16].any():
                            freer[y:y + 16, x:x + 16] = True
                            n += 1
                res.append((gridrows * ncol + n, ncol, gridrows, y0, gap, n))
res.sort(reverse=True)
seen = set()
P('   ncol rows y0 gap | 网格格位 | 额外可加 | 合计上限')
for (tot, ncol, gridrows, y0, gap, n) in res:
    if tot in seen:
        continue
    seen.add(tot)
    P('    %2d   %2d   %d  +%d |  %4d   |   %3d    |  %4d' % (ncol, gridrows, y0, gap, gridrows * ncol, n, tot))
P('')
if res:
    b = res[0]
    P('   ★★ 图集能容纳的对偶字形上限 ≈ **%d** 个' % b[0])
    P('   ★★ 相对现役 1736 ⇒ **最多再加 %d 个新字**' % (b[0] - 1736))
    P('   （现役 1736 必须整体重铺到该布局；且这是"零浪费"下界，实际会更少）')

P('')
P('=' * 78)
P('③ 364 个新字需要多少格位？')
P('   1736(现役) + 364(新) = 2100 个对偶字形 = 2100 格位')
P('   加上 ASCII 段 95 格 + 单字节汉字 106 格 = 2301 格位')
P('   图集只有 2048 格位 ⇒ 缺口 253 格位')
P('   ⇒ 结论：**364 个新字在 1024x512/h=512 的图集里物理上放不下**')

with io.open(os.path.join(OUT, 'ceiling.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'ceiling.txt'))
