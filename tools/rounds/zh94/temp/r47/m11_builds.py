# -*- coding: utf-8 -*-
r"""m11_builds.py — round47 ⑪: 各构筑盘的图集几何 + 记录矩形处内容对照 (找"干净"参照)。

重点:
  · 记录矩形 (89,395,135,408) / (136,420,146,436) 手柄图标 —— ZH9x 各盘是否有污染;
  · 行 18 记录格 (592..991, 338..353) 的末行 (353) —— 哪个盘是干净的。
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, rects_all, default_rects  # noqa: E402
import numpy as np                                                                 # noqa: E402
import tcslib                                                                      # noqa: E402

VERS = [v for v in ('GR_ZH91', 'GR_ZH92', 'GR_ZH93', 'GR_ZH94')
        if os.path.isfile(os.path.join(REPO, 'work', 'builds', v, v + '.iso'))]
eng = {}
for v in VERS:
    try:
        A = load(v, want_ft=(v == 'GR_ZH93'))
        eng[v] = A['eng']
        print('%-10s PX=%-6d px_size=%-7d 段=%d 墨=%d'
              % (v, A['PX'], A['px_size'], len(A['segs']), A['eng'].sum()))
    except Exception as e:                                            # noqa: BLE001
        print('%-10s 读不出: %s' % (v, e))

Z = eng['GR_ZH93']
print()
print('=' * 78)
print('① 手柄图标矩形逐行 (各行"墨点位置"对照)')
for (u0, v0, u1, v1) in ((88, 394, 136, 409), (135, 419, 147, 437)):
    print('  --- 矩形 (u=%d..%d, v=%d..%d) ---' % (u0, u1, v0, v1))
    for y in range(v0, v1 + 1):
        line = []
        for v in VERS:
            xs = np.where(eng[v][y, u0:u1])[0]
            line.append('%s:n=%2d' % (v[-4:], len(xs)))
        base = np.where(Z[y, u0:u1])[0]
        print('   v=%3d  %s   ZH93 墨点: %s' % (y, '  '.join(line), (base + u0).tolist()[:14]))

print()
print('=' * 78)
print('② 行 18 单字节记录格 (592..991, 338..353) 的**末行 353** 在各盘的内容')
dflt = default_rects(load('GR_ZH93', want_ft=True)['faces'])
for code in (0xC2, 0xC4, 0xC5, 0xCE, 0xD3, 0xD6, 0xD8, 0xDA):
    u0, v0, u1, v1 = dflt[code]
    print('  0x%02X u=%d..%d' % (code, u0, u1))
    for v in VERS:
        xs = (np.where(eng[v][v0 + 15, u0:u1])[0] + u0).tolist()
        print('     %s v=%d 墨点 %s' % (v, v0 + 15, xs))
