# -*- coding: utf-8 -*-
r"""zx_r84_cap3.py — round84：**具体布局求解 + 天花板**（只读）

目标：给出「gap 3->0、h=512、容器不动」下的**确切**新字上限，而不是估算。
做法：对每个候选布局参数 (ncol, y0, 记录带位置)，把
        · 1736 个现役对偶格位（必须保留 y 公式）
        · 208 个唯一记录矩形（可自由平移，但必须 16 行对齐）
        · N 个新字格位
      一起塞进 1024x512，用「先放记录 → 再放格位」的确定性算法求最大 N。

产出 work/builds/GR_ZH98/temp/r84/cap3.txt
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
P('GR_ZH123 ; 唯一记录矩形 %d（宽分布 %s ; 高分布 %s）'
  % (len(rects),
     dict(sorted({w: sum(1 for r in rects if r[2] - r[0] == w) for w in {r[2] - r[0] for r in rects}}.items())),
     dict(sorted({h: sum(1 for r in rects if r[3] - r[1] == h) for h in {r[3] - r[1] for r in rects}}.items()))))
P('')


# ── 记录：可任选 (x,y)，但 y 必须 16 对齐（与格位同一套 stride）──
def pack_records(free, yalign=16):
    f = free.copy()
    out = {}
    order = sorted(rects, key=lambda r: (-(r[2] - r[0]), -(r[3] - r[1])))
    for (u0, v0, u1, v1) in order:
        w, h = u1 - u0, v1 - v0
        got = None
        for y in range(0, H - h + 1, yalign):
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


def run(**kw):
    ncol = kw['ncol']
    y0 = kw.get('y0', 0)
    gaprow = kw.get('gaprow', 99)
    gap = kw.get('gap', 0)
    gridrows = kw['gridrows']
    n_double = kw['n_double']          # 需要放下的对偶字形总数（含现役）
    busy = np.zeros((H, W), bool)
    # 1) 记录优先（可放在任何 16 对齐 y）
    r = pack_records(~busy)
    if r is None:
        return None
    _, free = r
    # 2) 格位：按 slot 顺序走，能放就放
    placed = 0
    free2 = free.copy()
    for s in range(gridrows * ncol):
        row, col = divmod(s, ncol)
        y = y0 + 16 * (row + (gap if row >= gaprow else 0))
        x = 16 * col
        if y + 16 > H or x + 16 > W:
            return None
        if not free2[y:y + 16, x:x + 16].any():
            free2[y:y + 16, x:x + 16] = True
            placed += 1
    return placed, int(free2.sum()), gridrows * ncol


P('=' * 78)
P('求解：记录先占位（16 行对齐），再按 slot 顺序填格位；报「能填几个格位」')
P('   ncol rows y0 gap | 可填格位 | 还能加新字(=格位-1736) | 剩余 texel')
res = []
for ncol in (62, 63, 64):
    for gridrows in range(28, 34):
        for y0 in (0, 2):
            r = run(ncol=ncol, y0=y0, gridrows=gridrows, n_double=0)
            if r is None:
                continue
            placed, left, total = r
            res.append((placed, ncol, gridrows, y0, left))
res.sort(reverse=True)
seen = set()
for (placed, ncol, gridrows, y0, left) in res:
    k = placed
    if k in seen:
        continue
    seen.add(k)
    P('    %2d   %2d   %d  +0 |   %4d   |       +%4d        | %7d'
      % (ncol, gridrows, y0, placed, placed - 1736, left))

P('')
P('=' * 78)
P('★ 结论')
if res:
    b = res[0]
    P('   最好布局: ncol=%d, rows=%d, y0=%d -> 可填 **%d** 个对偶格位' % (b[1], b[2], b[3], b[0]))
    P('   现役 1736 ⇒ **最多再加 %d 个新字**（且现役 1736 必须整体重铺到这一布局）' % (b[0] - 1736))

with io.open(os.path.join(OUT, 'cap3.txt'), 'w', encoding='utf-8', newline='\n') as f:
    f.write('\n'.join(B) + '\n')
print('\n[out] %s' % os.path.join(OUT, 'cap3.txt'))
