# -*- coding: utf-8 -*-
r"""m10_en.py — round47 ⑩: 拿**原版 EN 盘**当"真值"比对记录矩形 (原版内容没被我们改过的那些)。

EN 盘 = 单包裸图 ⇒ 引擎口径图里的行 = 容器 payload 行, 与我们 8 段容器的 payload 行一致
(段号 = 行//64), 所以同一 (u,v) 可以直接比。
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, rects_all, default_rects  # noqa: E402
import numpy as np                                                                 # noqa: E402
import tcslib                                                                      # noqa: E402

EN = load('GR_EN_ORIG')
Z93 = load('GR_ZH93')
en, a93 = EN['eng'], Z93['eng']
print('EN 段表: %s' % ([tuple(int(v) for v in s) for s in EN['segs']],))
print('EN 墨量 %d; ZH93 墨量 %d' % (en.sum(), a93.sum()))

rects = rects_all(Z93['faces'])
res = []
for fname, code, u0, v0, u1, v1 in rects:
    if u1 <= u0 or v1 <= v0:
        continue
    x0, x1 = max(0, u0), min(W, u1)
    y0, y1 = max(0, v0), min(H, v1)
    e = en[y0:y1, x0:x1]
    z = a93[y0:y1, x0:x1]
    d = int((e != z).sum())
    res.append(dict(face=fname, code=code, u0=u0, v0=v0, u1=u1, v1=v1,
                    diff=d, en_ink=int(e.sum()), z_ink=int(z.sum()), tot=int(e.size)))
print()
print('=' * 78)
print('544 条记录: EN 原版 vs ZH93 的差异')
g = collections.defaultdict(list)
for r in res:
    g[(r['face'], r['v0'], r['u1'] - r['u0'], r['v1'] - r['v0'])].append(r)
for k in sorted(g, key=lambda z: (z[0], z[1])):
    v = g[k]
    same = sum(1 for r in v if r['diff'] == 0)
    print('  face=%-8s v0=%-4d %2dx%2d  %3d 条: 与 EN 相同 %3d, 不同 %3d  (差异最大 %d)'
          % (k[0], k[1], k[2], k[3], len(v), same, len(v) - same,
             max(r['diff'] for r in v)))
print()
print('  --- 与 EN 相同 (没被我们改过) 的记录, 按 v0 ---')
for k in sorted(g, key=lambda z: (z[0], z[1])):
    v = [r for r in g[k] if r['diff'] == 0]
    if v:
        print('    face=%-8s v0=%-4d %2dx%2d : %d 条 码 %s'
              % (k[0], k[1], k[2], k[3], len(v), ' '.join('0x%02X' % r['code'] for r in v[:20])))
print()
print('  --- 三方对照: 与 EN 不同 且 v0 在 338/354/434 的记录 ---')
dflt = default_rects(Z93['faces'])
for r in res:
    if r['face'] != 'default' or r['v0'] not in (338, 354, 434):
        continue
    print('    0x%02X u=%4d v=%3d  EN墨=%4d ZH93墨=%4d 差=%3d/%d'
          % (r['code'], r['u0'], r['v0'], r['en_ink'], r['z_ink'], r['diff'], r['tot']))

# ---------- 图标矩形 ASCII 对照 ----------
print()
print('=' * 78)
print('手柄图标矩形: EN vs ZH93 (若 EN 干净, ZH93 多出来的墨 = 我们造成的污染)')
ICONS = sorted(set((r['u0'], r['v0'], r['u1'], r['v1']) for r in res if r['v0'] in (395, 420)))
for (u0, v0, u1, v1) in ICONS:
    print('  矩形 (u=%d..%d, v=%d..%d)  码 %s'
          % (u0, u1, v0, v1, ' '.join('0x%02X' % r['code'] for r in res
                                      if (r['u0'], r['v0']) == (u0, v0))))
    for tag, img in (('EN ', en), ('Z93', a93)):
        for y in range(v0 - 1, v1 + 2):
            print('   %s %3d |%s|' % (tag, y, ''.join('#' if img[y, x] else '.'
                                                     for x in range(u0 - 1, u1 + 1))))
    d = np.where(en[v0:v1, u0:u1] != a93[v0:v1, u0:u1])
    print('   → 差异像素 %d 个: %s' % (len(d[0]),
                                      [(int(v0 + y), int(u0 + x)) for y, x in list(zip(*d))[:40]]))
