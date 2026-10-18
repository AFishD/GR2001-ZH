# -*- coding: utf-8 -*-
r"""m1_measure.py — round47 ①: 定量测 GR_ZH93 vs GR_ZH94 的引擎口径图集差异。

要回答:
  A. 逐行差异: 哪些 y 变了, 是不是"整块下移一行"(B[y] == A[y-1])?
  B. 544 条 FT 记录矩形: 每条矩形内 A vs B 的关系 (相同 / 下移 k 行 / 上移 k 行 / 其他)。
  C. 汉字格 (对偶槽位) 区域: 是否有同类"多贴一行"的现象。
"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import (REPO, W, H, NCOL, CW, CH, yrow, load, rects_all,     # noqa: E402
                    default_rects, ascii_dump)
import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402

A93 = load('GR_ZH93')
A94 = load('GR_ZH94')
a93, a94 = A93['eng'], A94['eng']
print('=' * 78)
print('图集 (引擎口径) 墨量: GR_ZH93=%d  GR_ZH94=%d' % (a93.sum(), a94.sum()))
print('段表: %s' % ([tuple(int(v) for v in s) for s in A93['segs']],))
print('段表 (94): %s' % ([tuple(int(v) for v in s) for s in A94['segs']],))
print('px_off PX: 93=%d 94=%d  px_size 93=%d 94=%d' %
      (A93['PX'], A94['PX'], A93['px_size'], A94['px_size']))

# FONT.RES 是否逐字节相同 (记录表没被动过?)
print('FONT.RES 展开态相同: %s (93 长 %d / 94 长 %d)'
      % (A93['ft_blob'] == A94['ft_blob'], len(A93['ft_blob']), len(A94['ft_blob'])))

# ---------- A. 逐行差异 ----------
print()
print('=' * 78)
print('A. 逐行差异 (整宽 1024) ——  仅列 y>=300')
print('     y     diff   |B[y]==A[y-1]|   |B[y]==A[y]|   说明')
rows_shift, rows_diff = [], []
for y in range(300, H):
    d = int((a93[y] != a94[y]).sum())
    if d == 0:
        continue
    eq_prev = int((a94[y] == a93[y - 1]).sum()) if y > 0 else -1
    eq_same = W - d
    rows_diff.append(y)
    if eq_prev == W:
        rows_shift.append(y)
    print('   %4d   %5d      %5d          %5d      %s'
          % (y, d, eq_prev, eq_same, '← 整行 = 上一行' if eq_prev == W else ''))
print()
print('有差异的行: %d 行, y=%d..%d' % (len(rows_diff), min(rows_diff), max(rows_diff)))
print('其中"整行 == 上一行"的行: %d 行 %s' % (len(rows_shift), rows_shift[:40]))
band = []
for r in range(19, 25):
    band += list(range(yrow(r), yrow(r) + CH))
print('6 条行带 (row19..24) 覆盖 y=%d..%d, 行数=%d' % (min(band), max(band), len(band)))
print('带外有差异的行: %s' % (sorted(set(rows_diff) - set(band))[:20]))
print('带内**没有**差异的行: %s'
      % (sorted(set(band) - set(rows_diff))[:40]))

# ---------- A2. 缩小到 中 那一列带 (u=896..1000) ----------
print()
print('=' * 78)
print('A2. 细看 (u=880..1000, y=330..375): 93 vs 94 逐行墨点')
for tag, img in (('93', a93), ('94', a94)):
    print('  --- GR_ZH%s ---' % tag)
    for y in range(330, 376):
        xs = np.where(img[y, 880:1000])[0] + 880
        print('   v=%3d n=%2d %s' % (y, len(xs), xs.tolist()[:26]))

# ---------- B. FT 记录矩形 ----------
print()
print('=' * 78)
rects = rects_all(A93['faces'])
print('B. 3 个 face 的 FT 记录矩形共 %d 条; 逐条比 A(93) vs B(94) 在矩形内 (u0..u1, v0..v1)' % len(rects))
res = []
for fname, code, u0, v0, u1, v1 in rects:
    if u1 <= u0 or v1 <= v0:
        res.append(dict(face=fname, code=code, u0=u0, v0=v0, u1=u1, v1=v1, kind='空矩形'))
        continue
    x0, x1 = max(0, u0), min(W, u1)
    y0, y1 = max(0, v0), min(H, v1)
    if x0 >= x1 or y0 >= y1:
        res.append(dict(face=fname, code=code, u0=u0, v0=v0, u1=u1, v1=v1, kind='越界'))
        continue
    r93 = a93[y0:y1, x0:x1]
    r94 = a94[y0:y1, x0:x1]
    same = int((r93 == r94).sum())
    tot = r93.size
    # 各种位移假设: B[y] = A[y-k]
    shifts = {}
    for k in (-3, -2, -1, 1, 2, 3):
        yy0, yy1 = max(y0, k), min(y1, H + k)
        if yy0 >= yy1:
            continue
        sub93 = a93[yy0 - k:yy1 - k, x0:x1]
        sub94 = a94[yy0:yy1, x0:x1]
        shifts[k] = int((sub93 == sub94).sum())
    best = None
    for k, v in shifts.items():
        if v == (min(y1, H + k) - max(y0, k)) * (x1 - x0):
            best = k
            break
    kind = '相同' if same == tot else ('下移%d行' % best if best and best > 0 else
                                      ('上移%d行' % -best if best and best < 0 else '不同'))
    res.append(dict(face=fname, code=code, u0=u0, v0=v0, u1=u1, v1=v1, w=x1 - x0, h=y1 - y0,
                    same=same, tot=tot, kind=kind, shifts=shifts))
import collections                                                     # noqa: E402
cnt = collections.Counter((r['kind'], r['face']) for r in res)
print('  分类 (kind, face) → 条数:')
for k in sorted(cnt, key=lambda x: (x[1], x[0])):
    print('    %-12s %-8s %d' % (k[0], k[1], cnt[k]))
print('  合计 %d 条' % len(res))
print()
print('  ★ 有位移的记录明细 (前 40):')
for r in res:
    if r['kind'] not in ('相同', '空矩形', '越界'):
        print('    face=%-8s 0x%02X 矩形 u=%d..%d v=%d..%d (%dx%d)  kind=%s  same=%d/%d  shifts=%s'
              % (r['face'], r['code'], r['u0'], r['u1'], r['v0'], r['v1'], r['w'], r['h'],
                 r['kind'], r['same'], r['tot'], r['shifts']))
        if len([1 for q in res if q['kind'] not in ('相同', '空矩形', '越界')]) > 40:
            break
seen = [r for r in res if r['kind'] not in ('相同', '空矩形', '越界')]
print('  (共 %d 条非"相同")' % len(seen))

# ---------- B2. default face 的 v0 分布 + 按行带统计 ----------
print()
print('  default face 记录 v0 分布 (top 12): %s'
      % collections.Counter(r['v0'] for r in res if r['face'] == 'default').most_common(12))
print('  3 个 face 记录 v0 分布 (top 12): %s'
      % collections.Counter(r['v0'] for r in res).most_common(12))

# ---------- C. 汉字格 (对偶槽) ----------
print()
print('=' * 78)
print('C. 对偶槽 (汉字格) 区域: 引擎格 (16*col, yrow(row)) 在 93 vs 94 的关系')
cs = tcslib.Charset()
by_slot = {}
for ch, (b1, b2) in cs.enc_pair.items():
    by_slot[tcslib.pair_slot(b1, b2)] = ch
print('  charset 里已用对偶槽 %d 个' % len(by_slot))
cat = collections.Counter()
detail = []
for slot, ch in sorted(by_slot.items()):
    row, col = slot // NCOL, slot % NCOL
    y0, x0 = yrow(row), col * CW
    if y0 + CH > H or x0 + CW > W:
        cat['越界'] += 1
        continue
    c93 = a93[y0:y0 + CH, x0:x0 + CW]
    c94 = a94[y0:y0 + CH, x0:x0 + CW]
    same = int((c93 == c94).sum())
    # 位移假设: B[y] = A[y-k]
    sd = su = 0
    for k in (1, 2, 3):
        if y0 + k + CH <= H:
            sub = a93[y0 + k:y0 + k + CH, x0:x0 + CW]
            if (sub == c94).all():
                sd = k
                break
    for k in (1, 2, 3):
        if y0 - k >= 0:
            sub = a93[y0 - k:y0 - k + CH, x0:x0 + CW]
            if (sub == c94).all():
                su = k
                break
    if same == CH * CW:
        cat['逐像素相同'] += 1
    elif sd:
        cat['整格下移%d行' % sd] += 1
        detail.append((row, col, ch, '下移%d' % sd))
    elif su:
        cat['整格上移%d行' % su] += 1
        detail.append((row, col, ch, '上移%d' % su))
    else:
        cat['其他不同'] += 1
        detail.append((row, col, ch, '其他 (%d/%d 相同)' % (same, CH * CW)))
for k, v in cat.most_common():
    print('    %-16s %d' % (k, v))
print('  ★ row19..24 上有变化的对偶槽 (前 60):')
for row, col, ch, w in detail:
    if 19 <= row <= 24:
        print('    row%-2d col%-2d %s  %s' % (row, col, ch, w))
print('  (共 %d 个对偶槽有变化, 其中 row19..24 = %d)'
      % (len(detail), sum(1 for d in detail if 19 <= d[0] <= 24)))

# ---------- D. 保存 ----------
out = os.path.join(HERE, 'm1_measure.json')
io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
    ink93=int(a93.sum()), ink94=int(a94.sum()),
    rows_diff=rows_diff, rows_shift=rows_shift,
    ft_same=A93['ft_blob'] == A94['ft_blob'],
    rect_kinds=dict(('%s|%s' % (k[0], k[1]), v) for k, v in cnt.items()),
    rects=[dict((k, v) for k, v in r.items() if k != 'shifts') for r in res],
    dual=dict((k, v) for k, v in cat.items()),
), ensure_ascii=False, indent=1) + '\n')
print()
print('[out] → %s' % out)
