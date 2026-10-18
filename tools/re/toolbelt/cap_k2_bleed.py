# -*- coding: utf-8 -*-
r"""cap_k2_bleed.py -- SKIP=2 的关键实测: 网格格的**逐行墨分布** (决定"1~3 行渗漏"是否可见)

问题: 新布局下 grid row12 = y226..241。旧跳过带里那些 ASCII 记录 (v0=211 → 行 211..226,
v0=213 → 行 213..228) 的**最后 1~3 行**现在落在 grid row12 的**前 1~3 行**上。
若 grid 格的前几行本来就没墨 ⇒ 该行仍为空 ⇒ ASCII 字形像素**不变** ✓

本脚本实测 (只读基底 GR_ZH124):
  ① 全部 1736 个现役格 (老布局 62 列/SKIP=3) 的格内逐行墨量直方图;
  ② 将要落到新 row12 / row11 / row13 的槽 (768..831 / 704..767 / 832..895) 的逐行墨;
  ③ 若把 x 分列成 8px 列, 看 row12 各行在哪些 x 上确有墨 (与 ASCII 记录 x 区间比对);
  ④ 逐格 "前 4 行有无墨" 的名单。
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
NCOL_OLD, SKIP_OLD = 62, 3
NCOL_NEW, SKIP_NEW = 64, 2
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip):
    return 2 + 16 * (row + (skip if row >= 12 else 0))


def plane_of(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e = [x for x in ent if x['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso.read(e['iso_off'], e['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, _c = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    iso.close()
    return img


def main():
    img = plane_of(os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso'))
    # ① 老布局逐格逐行墨
    prof = np.zeros(16, dtype=int)
    cells = 0
    for s in range(1736):
        r, c = s // NCOL_OLD, s % NCOL_OLD
        x, y = 16 * c, yrow(r, SKIP_OLD)
        cell = img[y:y + 16, x:x + 16]
        prof += cell.sum(axis=1)
        cells += 1
    P('[prof] 老布局 %d 个现役格的**格内逐行墨量** (总计):' % cells)
    for i in range(16):
        P('    cell row %2d : %7d texel (%.2f/格)' % (i, prof[i], prof[i] / float(cells)))
    P('')
    # ② 新布局的关键行
    for newrow, lo, hi in ((11, 704, 767), (12, 768, 831), (13, 832, 895)):
        P('[key ] 新 row%d (y=%d..%d) ← 槽 %d..%d (老布局的格):'
          % (newrow, yrow(newrow, SKIP_NEW), yrow(newrow, SKIP_NEW) + 15, lo, hi))
        agg = np.zeros(16, dtype=int)
        firstink = []
        for s in range(lo, hi + 1):
            r, c = s // NCOL_OLD, s % NCOL_OLD
            x, y = 16 * c, yrow(r, SKIP_OLD)
            cell = img[y:y + 16, x:x + 16]
            agg += cell.sum(axis=1)
            ri = [int(i) for i in range(16) if cell[i].any()]
            firstink.append((s, ri[0] if ri else -1, x, y))
        for i in range(16):
            P('    新格 row %2d : %6d texel' % (i, agg[i]))
        bad = [t for t in firstink if t[1] in (0, 1, 2)]
        P('    ★ 首墨行 ≤2 的槽 **%d** 个 (前 3 行有墨): %s'
          % (len(bad), [(s, ri, x) for (s, ri, x, _y) in bad]))
        P('    ★ 首墨行 == 0 的槽: %s' % [(s, x) for (s, ri, x, _y) in firstink if ri == 0])
    # ③ 新布局 row12 的逐 x 墨 (按 8px 列统计)
    P('')
    P('[xmap] 新 row12 (y=%d) 在实际像素上的墨: 哪些 x 有墨 (由要落到这里的 64 个汉字格决定)'
      % yrow(12, SKIP_NEW))
    # 新 row12 的格内容 = 老布局槽 768..831 的格, 但 x 会变 (62→64 列)
    for i in range(4):
        yy = yrow(12, SKIP_NEW) + i
        row = np.zeros(W, dtype=bool)
        for s in range(768, 832):
            r, c = s // NCOL_OLD, s % NCOL_OLD
            xs, ys = 16 * c, yrow(r, SKIP_OLD)
            xd = 16 * (s % NCOL_NEW)
            row[xd:xd + 16] = img[ys + i, xs:xs + 16]
        n = int(row.sum())
        xs = np.nonzero(row)[0]
        P('    新 row12 第 %d 行 (y=%d): 墨 %d texel ; x 区间 %s'
          % (i, yy, n, ('%d..%d' % (xs.min(), xs.max())) if n else '-'))
    out = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'temp', 'k2_bleed.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
