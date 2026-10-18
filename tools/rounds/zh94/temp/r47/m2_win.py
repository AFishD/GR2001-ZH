# -*- coding: utf-8 -*-
r"""m2_win.py — round47 ②: 记录码的**采样窗** (u0+DU, v0+DV) 才是引擎真正看的 16x16。

要点:
  1. 用 中(0xD6) 的墨迹包围盒证明采样窗 = 记录矩形 +(4,2);
  2. 逐条记录比 ZH93 vs ZH94 在**采样窗**内的差异 (这才是用户看到的脏像素);
  3. 统计两套保护口径 (raw rect / window) 下, grid 行 19..24 的占格/空闲。
"""
import collections
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

DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV
A93 = load('GR_ZH93')
A94 = load('GR_ZH94')
a93, a94 = A93['eng'], A94['eng']
rects = rects_all(A93['faces'])
print('=' * 78)
print('GLYPH_DU/DV = %d/%d ; 记录条数(3 face) = %d' % (DU, DV, len(rects)))

# ---------- 1. 中(0xD6) 的墨迹包围盒 ----------
print()
print('=' * 78)
print('1. 中 = 单字节码 0xD6 的记录矩形与墨迹包围盒 (决定采样窗口到底在哪)')
dflt = default_rects(A93['faces'])
for code in (0xD6, 0xD5, 0xD7, 0xE2):
    u0, v0, u1, v1 = dflt[code]
    win = (u0 + DU, v0 + DV, u0 + DU + CW, v0 + DV + CH)
    for tag, img in (('93', a93), ('94', a94)):
        sub = img[v0:v0 + 40, u0 - 8:u1 + 24]
        ys, xs = np.where(sub)
        if len(ys):
            print('  0x%02X %s: 矩形 u=%d..%d v=%d..%d  墨迹包围盒 u=%d..%d v=%d..%d'
                  % (code, tag, u0, u1, v0, v1,
                     u0 - 8 + xs.min(), u0 - 8 + xs.max(), v0 + ys.min(), v0 + ys.max()))
        else:
            print('  0x%02X %s: 无墨' % (code, tag))
    print('      采样窗(假设) = u=%d..%d v=%d..%d' % (win[0], win[2] - 1, win[1], win[3] - 1))
print()
print('  --- 中 0xD6 附近 ASCII (x=896..960, y=334..372) 列尺每 16 px ---')
print('        ' + ''.join(('%d' % ((x // 16) % 10)) if x % 16 == 0 else ' ' for x in range(896, 960)))
for tag, img in (('93', a93), ('94', a94)):
    print('  === GR_ZH%s ===' % tag)
    for line in ascii_dump(img, 896, 960, 334, 372):
        print('  ' + line)

# ---------- 2. 逐条记录: 采样窗内 93 vs 94 ----------
print()
print('=' * 78)
print('2. 逐条记录: 在**采样窗** (u0+%d..u1+%d, v0+%d..v1+%d) 内比 93 vs 94' % (DU, DU, DV, DV))
res = []
for fname, code, u0, v0, u1, v1 in rects:
    x0, y0 = u0 + DU, v0 + DV
    x1, y1 = u1 + DU, v1 + DV
    if not (0 <= x0 < x1 <= W and 0 <= y0 < y1 <= H):
        res.append(dict(face=fname, code=code, u0=u0, v0=v0, u1=u1, v1=v1, win_ok=False))
        continue
    w93 = a93[y0:y1, x0:x1]
    w94 = a94[y0:y1, x0:x1]
    d = int((w93 != w94).sum())
    res.append(dict(face=fname, code=code, u0=u0, v0=v0, u1=u1, v1=v1, win_ok=True,
                    win=[x0, y0, x1, y1], diff=d, ink93=int(w93.sum()), ink94=int(w94.sum())))
bad = [r for r in res if r.get('win_ok') and r['diff']]
print('  采样窗内**有差异**的记录: %d / %d' % (len(bad), sum(1 for r in res if r.get('win_ok'))))
print('  按 face: %s' % collections.Counter(r['face'] for r in bad).most_common())
print('  按 v0:   %s' % collections.Counter(r['v0'] for r in bad).most_common())
print('  按 v0 (default face only): %s'
      % collections.Counter(r['v0'] for r in bad if r['face'] == 'default').most_common())
print()
print('  ★ default face 受影响记录明细:')
for r in bad:
    if r['face'] != 'default':
        continue
    print('    0x%02X 矩形 u=%d..%d v=%d..%d  窗 u=%d..%d v=%d..%d  差 %d 像素 (墨 93=%d 94=%d)'
          % (r['code'], r['u0'], r['u1'], r['v0'], r['v1'], r['win'][0], r['win'][2],
             r['win'][1], r['win'][3], r['diff'], r['ink93'], r['ink94']))
print()
print('  ★ 全部 3 face 受影响记录 (u0, v0, 差像素):')
for r in bad:
    print('    %-8s 0x%02X u=%d v=%d 窗=%s 差=%d' % (r['face'], r['code'], r['u0'], r['v0'],
                                                    r['win'], r['diff']))

# 矩形内 vs 窗内: 对照 (证明"矩形内 0 差异"抓不到这个 bug)
rectbad = 0
for fname, code, u0, v0, u1, v1 in rects:
    if u1 <= u0 or v1 <= v0:
        continue
    x0, x1 = max(0, u0), min(W, u1)
    y0, y1 = max(0, v0), min(H, v1)
    if (a93[y0:y1, x0:x1] != a94[y0:y1, x0:x1]).any():
        rectbad += 1
print()
print('  [对照] 在**原始矩形**内有差异的记录: %d / %d  ← 用这个口径查不出问题' % (rectbad, len(rects)))

# ---------- 3. 两套保护口径的占格统计 ----------
print()
print('=' * 78)
print('3. grid 行 19..24 (6 行 62 列 = 372 格) 在两种保护口径下的占用')
ROWS = list(range(19, 25))
pr_rect = np.zeros((H, W), dtype=bool)
pr_win = np.zeros((H, W), dtype=bool)
for fname, code, u0, v0, u1, v1 in rects:
    if u1 <= u0 or v1 <= v0:
        continue
    pr_rect[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True
    pr_win[max(0, v0 + DV):min(H, v1 + DV), max(0, u0 + DU):min(W, u1 + DU)] = True
cs = tcslib.Charset()
used = set()
for ch, (b1, b2) in cs.enc_pair.items():
    used.add(tcslib.pair_slot(b1, b2))
print('  charset 已用对偶槽: %d 个 (其中 grid 行 19..24 上: %d)'
      % (len(used), sum(1 for s in used if 19 <= s // NCOL <= 24)))
for name, pr in (('raw rect', pr_rect), ('window', pr_win)):
    blk = [1 if pr[yrow(r):yrow(r) + CH, c * CW:(c + 1) * CW].any() else 0
           for r in ROWS for c in range(NCOL)]
    nblk = sum(blk)
    nused_blk = sum(1 for i, r in enumerate([(rr, cc) for rr in ROWS for cc in range(NCOL)])
                    if blk[i] and (r[0] * NCOL + r[1]) in used)
    nfree = sum(1 for i, r in enumerate([(rr, cc) for rr in ROWS for cc in range(NCOL)])
                if not blk[i] and (r[0] * NCOL + r[1]) not in used)
    print('  口径=%-9s 被压格 %3d, 其中已用 %3d; 干净空闲格 %3d' % (name, nblk, nused_blk, nfree))
print()
print('  按行 (window 口径): row → 被压列号')
for r in ROWS:
    cols = [c for c in range(NCOL)
            if pr_win[yrow(r):yrow(r) + CH, c * CW:(c + 1) * CW].any()]
    uc = [c for c in cols if (r * NCOL + c) in used]
    free = [c for c in range(NCOL) if c not in cols and (r * NCOL + c) not in used]
    print('    row%-2d 被压 %2d 列 %s' % (r, len(cols), cols))
    print('           其中已用 %2d %s' % (len(uc), uc))
    print('           干净空闲 %2d %s' % (len(free), free))

io.open(os.path.join(HERE, 'm2_win.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps(dict(rects=res, rows_win=dict(
        (str(r), [c for c in range(NCOL)
                  if pr_win[yrow(r):yrow(r) + CH, c * CW:(c + 1) * CW].any()]) for r in ROWS),
    ), ensure_ascii=False, indent=1) + '\n')
print()
print('[out] → m2_win.json')
