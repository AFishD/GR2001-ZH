# -*- coding: utf-8 -*-
"""r50 临时: 在图集里"按位图搜索"这 7 个字形的 15 行特征块, 看它在各版本盘上是否有底行。

做法: 取 GR_ZH97 上 宇/孙/宁 的**上 15 行** (16 列) 当模板, 在目标盘的引擎图上按
x 对齐 16 的整格滑动匹配; 命中后打印该处 16x16 与命中位置下方 1 行是否有墨。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))

import numpy as np                                     # noqa: E402
import dump_font                                       # noqa: E402


def eng(rel):
    font = dump_font.load_font(os.path.join(REPO, rel))
    g = dump_font.atlas_gray(font['atlas'], view='engine')
    W, H = font['atlas']['w'], font['atlas']['h']
    return (np.frombuffer(g, np.uint8).reshape(H, W) == 0), W, H


REF, W, H = eng('work/builds/GR_ZH97/GR_ZH97.iso')
PAT = {}
for ch, (x, y) in (('宇', (560, 370)), ('孙', (528, 370)), ('宁', (544, 370))):
    PAT[ch] = REF[y:y + 15, x:x + 16].copy()
    print('模板 %s: 15 行 x 16 列, 墨=%d' % (ch, PAT[ch].sum()))

for rel in ('work/builds/GR_ZH91/GR_ZH91.iso', 'work/builds/GR_ZH92/GR_ZH92.iso',
            'work/builds/GR_ZH93/GR_ZH93.iso', 'work/builds/GR_ZH94/GR_ZH94.iso',
            'work/builds/GR_ZH95/GR_ZH95.iso', 'work/builds/GR_ZH97/GR_ZH97.iso',
            'work/builds/GR_ZH98/GR_ZH98.iso'):
    tag = rel.split('/')[2]
    A, w, h = eng(rel)
    print('=== %s' % tag)
    for ch in ('宇', '孙', '宁'):
        p = PAT[ch]
        hits = []
        for yy in range(0, h - 16):
            for cc in range(0, w // 16):
                xx = cc * 16
                if np.array_equal(A[yy:yy + 15, xx:xx + 16], p):
                    below = int(A[yy + 15, xx:xx + 16].sum()) if yy + 15 < h else -1
                    hits.append((xx, yy, below))
        # 只保留"下方整格 16x16 里墨最少"的命中, 过滤掉偶合
        uniq = sorted(set(hits))
        print('   %s 命中 %d 处: %s' % (ch, len(uniq),
                                        '; '.join('(%d,%d)下方第1行墨=%d' % t for t in uniq[:6])))
