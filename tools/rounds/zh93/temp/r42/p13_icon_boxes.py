# -*- coding: utf-8 -*-
r"""p13_icon_boxes.py — round42: 精确定位 pda_counterparts 里每个图标的位置, 与引擎 UV 对齐

做法: 背景 = 图里出现次数最多的颜色; 逐列统计「非背景」像素 ⇒ 找连通列区间 = 图标实际的 x 范围。
      再与 ELF 里硬编码的 UV 框逐一对照。
      最后把每个「声明 UV 框」单独裁出来拼成一张对照图 (左=0xB5框, 右=0xB1框 …)。
"""
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402
from PIL import Image                                            # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
NAME = 'pda_counterparts'

iso = tcslib.Iso(ISO)
pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
        break
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
base = 0
rec = None
while base + 8 <= len(pak):
    ty, nl = struct.unpack_from('<II', pak, base)
    if ty == 0x63 or nl > 64:
        break
    nm = pak[base + 8:base + 8 + nl].decode('latin-1')
    q = base + 8 + nl
    psm, w, h, clut = struct.unpack_from('<4I', pak, q)
    pxoff = q + 16 + clut
    pxsz = struct.unpack_from('<I', pak, q + 16 + clut)[0]
    if nm == NAME:
        rec = dict(psm=psm, w=w, h=h, cl=pak[q + 16:q + 16 + clut],
                   px=pak[pxoff + 4: pxoff + 4 + pxsz])
        break
    base = pxoff + 4 + pxsz
w, h, px, cl = rec['w'], rec['h'], rec['px'], rec['cl']
clut = cl[16:16 + 1024]


def rgb(i):
    o = i * 4
    return (clut[o], clut[o + 1], clut[o + 2])


# ── 背景色 = 全图出现最多的颜色 ──
cnt = Counter(px)
bg_idx = cnt.most_common(1)[0][0]
bg = rgb(bg_idx)
print('图 %dx%d psm=0x%02X; 背景索引 %d = RGB%s (占 %d/%d)'
      % (w, h, rec['psm'], bg_idx, bg, cnt[bg_idx], w * h))

# ── 行剖面: 找「图标行」 ──
print()
print('逐行「非背景」像素数 (只打 >0 的行, 分块):')
runs, cur = [], None
rowc = [sum(1 for x in range(w) if rgb(px[y * w + x]) != bg) for y in range(h)]
for y in range(h):
    if rowc[y] > 0 and cur is None:
        cur = y
    elif rowc[y] == 0 and cur is not None:
        runs.append((cur, y)); cur = None
if cur is not None:
    runs.append((cur, h))
print('  连续有内容的行区间: %s' % ' '.join('%d..%d' % r for r in runs))

for (v0, v1) in ((178, 198), (198, 218)):
    print()
    print('── 行带 v=%d..%d 的逐列内容 (找图标的真实 x 区间)' % (v0, v1))
    colc = [sum(1 for y in range(v0, v1) if rgb(px[y * w + x]) != bg) for x in range(w)]
    cruns, c = [], None
    for x in range(w):
        if colc[x] > 0 and c is None:
            c = x
        elif colc[x] == 0 and c is not None:
            cruns.append((c, x)); c = None
    if c is not None:
        cruns.append((c, w))
    print('   内容列区间: %s' % ' '.join('%d..%d(w%d)' % (a, b, b - a) for a, b in cruns))
    # 稀疏列 (按钮轮廓只有几列) 用阈值 2 再扫一遍
    c2, cruns2 = None, []
    for x in range(w):
        if colc[x] > 2 and c2 is None:
            c2 = x
        elif colc[x] <= 2 and c2 is not None:
            cruns2.append((c2, x)); c2 = None
    if c2 is not None:
        cruns2.append((c2, w))
    print('   (阈值>2)  %s' % ' '.join('%d..%d(w%d)' % (a, b, b - a) for a, b in cruns2))

# ── 把「引擎声明的 UV 框」逐个裁出来, 拼成对照图 ──
BOXES = [('0xB5', (1, 198, 21, 218)), ('0xB1', (25, 198, 45, 218)),
         ('49?', (49, 198, 69, 218)), ('73?', (73, 198, 93, 218)),
         ('sc26/28', (0, 178, 20, 198)), ('sc29', (21, 178, 41, 198)),
         ('sc30', (42, 178, 62, 198)), ('sc31', (63, 178, 83, 198)),
         ('sc27', (85, 178, 120, 198))]
S = 6
gap = 6
W = sum((b[2] - b[0]) * S + gap for _n, b in BOXES) + gap
H = 20 * S + 2 * gap
out = Image.new('RGB', (W, H), (255, 255, 255))
x = gap
for name, (u0, v0, u1, v1) in BOXES:
    tile = Image.new('RGB', (u1 - u0, v1 - v0))
    tp = tile.load()
    for yy in range(v0, v1):
        for xx in range(u0, u1):
            tp[xx - u0, yy - v0] = rgb(px[yy * w + xx])
    out.paste(tile.resize(((u1 - u0) * S, (v1 - v0) * S), Image.NEAREST), (x, gap))
    x += (u1 - u0) * S + gap
p = os.path.join(HERE, 'uv_boxes.png')
out.save(p)
print()
print('引擎声明的 UV 框逐个裁出 (顺序: %s) → %s'
      % (' | '.join(n for n, _b in BOXES), os.path.basename(p)))
