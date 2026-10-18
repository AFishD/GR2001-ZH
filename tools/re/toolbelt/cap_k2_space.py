# -*- coding: utf-8 -*-
r"""cap_k2_space.py -- SKIP=2 重做的**空间账**: 谁占了哪块 / 新布局下哪些记录被污染 / 哪里是空地

只读基底 GR_ZH124 (1024x512 / 62 列 / SKIP=3)。

输出:
  ① 基底占用图分类: 网格格 (老布局) / FT 记录窗 / 硬编码图标区 / 无人认领的墨
  ② 新布局 (h=644 / 64 列 / SKIP=2) 的网格墨图 ⇒ 逐条判定哪些 FT 记录被污染 (污染 texel 数)
  ③ 新布局下的**空闲区** (不被任何 <=2349 槽的格覆盖) 的矩形清单
  ④ 若 SKIP=3 (band 完整) 时空闲区清单 (对照: 证明只有 SKIP=2 才有整行空地)
"""
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

W = 1024
NCOL_OLD, SKIP_OLD, H_OLD = 62, 3, 512
NCOL_NEW, SKIP_NEW, H_NEW = 64, 2, 644
ICON_BOXES = [(1, 198, 21, 218), (25, 198, 45, 218)]     # icon_table.py 的硬编码 UV
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip):
    return 2 + 16 * (row + (skip if row >= 12 else 0))


def cell(slot, ncol, skip):
    return 16 * (slot % ncol), yrow(slot // ncol, skip)


def plane_and_recs(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e = [x for x in ent if x['name'] == 'COMMON.PAK'][0]
    eft = [x for x in ent if x['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e['iso_off'], e['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, _c = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    ft = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(eft['iso_off'], eft['stored']))))
    faces, _e = zx_lib.ft_records(ft, 28)
    iso.close()
    return img, faces


def grid_ink(img, ncol, skip, h, nslots, live_hi=1735):
    """新布局的网格墨图 (只写有墨的格): 返回 bool[h, W]

    ★ 只有槽 0..live_hi 在基底盘上有字形; 1736..2344 = 保留空槽; 2345..2349 = 借槽
      (落在 row36 col41..45, y=610, 与跳过带无关)。
    """
    out = np.zeros((h, W), dtype=bool)
    for s in range(min(nslots, live_hi + 1)):
        x, y = cell(s, ncol, skip)
        xs, ys = cell(s, NCOL_OLD, SKIP_OLD)
        out[y:y + 16, x:x + 16] = img[ys:ys + 16, xs:xs + 16]
    return out


def free_rects(blocked, y0, y1, min_w=8, min_h=16):
    """在 [y0,y1) 里找 min_h 行高、>=min_w 宽的全空矩形 (贪心扫描, 返回最大若干)"""
    out = []
    y = y0
    while y + min_h <= y1:
        # 该 min_h 行里全空的列
        band = ~blocked[y:y + min_h, :].any(axis=0)
        x = 0
        while x < W:
            if band[x]:
                x2 = x
                while x2 + 1 < W and band[x2 + 1]:
                    x2 += 1
                if x2 - x + 1 >= min_w:
                    out.append((x, x2 + 1, y, y + min_h))
                x = x2 + 1
            else:
                x += 1
        y += 1
    return out


def main():
    img, faces = plane_and_recs(os.path.join(REPO, 'work', 'builds', 'GR_ZH124',
                                             'GR_ZH124.iso'))
    # ── ① 基底占用 ──
    cellmask = np.zeros((H_OLD, W), dtype=bool)
    for s in range(1736):
        x, y = cell(s, NCOL_OLD, SKIP_OLD)
        cellmask[y:y + 16, x:x + 16] = True
    winmask = np.zeros((H_OLD, W), dtype=bool)
    recs = []
    for (nm, fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3]:
                winmask[r[3]:r[5], r[2]:r[4]] = True
                recs.append((nm, k, o, r))
    iconmask = np.zeros((H_OLD, W), dtype=bool)
    for (a, b, c, d) in ICON_BOXES:
        iconmask[b:d, a:c] = True
    ink = img
    orphan = ink & ~cellmask & ~winmask & ~iconmask
    P('① 基底占用 (1024x512):')
    P('    网格格 (1736 槽)    : %d texel' % int(cellmask.sum()))
    P('    记录窗 (%d 条非空)  : %d texel' % (len(recs), int(winmask.sum())))
    P('    图标区 (硬编码 UV×2) : %d texel' % int(iconmask.sum()))
    P('    ★ 墨总量 %d ; 「有墨但既不属于格也不属于任何窗/图标」= **%d** texel'
      % (int(ink.sum()), int(orphan.sum())))
    if orphan.sum():
        ys, xs = np.nonzero(orphan)
        P('      样例 (最多 12 个): %s' % list(zip(xs.tolist(), ys.tolist()))[:12])
        P('      y 范围 %d..%d ; 分带: %s'
          % (ys.min(), ys.max(), {int(b): int((orphan[b:b + 16].sum())) for b in range(0, 512, 16)
                                  if orphan[b:b + 16].sum()}))
    # ── ② 新布局网格墨 vs 记录窗 ──
    g_ink = grid_ink(img, NCOL_NEW, SKIP_NEW, H_NEW, 2350)
    P('')
    P('② 新布局 (h=644/64 列/SKIP=2) 网格墨 %d texel' % int(g_ink.sum()))
    bad = []
    for (nm, k, o, r) in recs:
        u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
        if v1 > H_NEW:
            continue
        sub = g_ink[v0:v1, u0:u1]
        n = int(sub.sum())
        if n:
            bad.append((nm, k, o, r, n))
    P('[bad] ★ 记录窗被网格墨污染: **%d** 条 (占非空 %d 条的 %.0f%%)'
      % (len(bad), len(recs), 100.0 * len(bad) / len(recs)))
    byface = {}
    for (nm, k, o, r, n) in bad:
        byface.setdefault(nm, []).append((k, r, n))
    for nm in sorted(byface):
        P('     %-8s %d 条' % (nm, len(byface[nm])))
    # 不重复的矩形
    dr = {}
    for (nm, k, o, r, n) in bad:
        dr.setdefault(r, []).append((nm, k, n))
    P('[bad] 其中**不同矩形 %d 个**; 尺寸分布 %s'
      % (len(dr), {k: sum(1 for r in dr if (r[4] - r[2], r[5] - r[3]) == k)
                   for k in sorted({(r[4] - r[2], r[5] - r[3]) for r in dr})}))
    P('[bad] 逐矩形 (u0,v0,u1,v1) 污染texel / 引用:')
    for r in sorted(dr, key=lambda r: (r[3], r[2])):
        P('      (%4d,%3d,%4d,%3d) %2dx%-2d 污染 %-4d ← %s'
          % (r[2], r[3], r[4], r[5], r[4] - r[2], r[5] - r[3],
             max(n for (_nm, _k, n) in dr[r]),
             ['%s#%d' % (nm, k) for (nm, k, _n) in dr[r]][:4]))
    # ── ③ 新布局空闲区 ──
    P('')
    P('③ 新布局的空闲区 (不被任何 0..2349 槽的格覆盖):')
    live_cells = np.zeros((H_NEW, W), dtype=bool)
    for s in range(2350):
        x, y = cell(s, NCOL_NEW, SKIP_NEW)
        live_cells[y:y + 16, x:x + 16] = True
    free = ~live_cells
    P('    总空闲 %d texel (%.1f 格)' % (int(free.sum()), free.sum() / 256.0))
    fr = free_rects(live_cells, 0, H_NEW, min_w=8, min_h=16)
    # 只列不重复的 (y, x0, x1)
    seen = set()
    P('    其中**高 >=16 行**的空带 (逐 y 起点; 去重后):')
    for (x0, x1, y0, y1) in fr:
        key = (x0, x1)
        if key in seen:
            continue
        seen.add(key)
        P('      y %3d..%-3d  x %4d..%-4d  宽 %4d px (= %3d 个 8px 槽 / %2d 个 16x16)'
          % (y0, y1 - 1, x0, x1 - 1, x1 - x0, (x1 - x0) // 8, (x1 - x0) // 16))
    P('    [注] y=642..643 与 y=0..1 只有 2 行高, 不能放 16 行窗')
    # ── ④ SKIP=3 对照 ──
    P('')
    P('④ 对照: 若 SKIP=3 (band 完整, 无渗漏) 的空闲区:')
    live3 = np.zeros((H_NEW, W), dtype=bool)
    for s in range(2350):
        x, y = cell(s, NCOL_NEW, 3)
        live3[y:y + 16, x:x + 16] = True
    P('    总空闲 %d texel (%.1f 格)' % (int((~live3).sum()), (~live3).sum() / 256.0))
    fr3 = free_rects(live3, 0, H_NEW, min_w=8, min_h=16)
    seen3 = set()
    for (x0, x1, y0, y1) in fr3:
        if (x0, x1) in seen3:
            continue
        seen3.add((x0, x1))
        P('      y %3d..%-3d  x %4d..%-4d  宽 %4d px (= %3d 个 8px 槽)'
          % (y0, y1 - 1, x0, x1 - 1, x1 - x0, (x1 - x0) // 8))
    out = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'temp', 'k2_space.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
