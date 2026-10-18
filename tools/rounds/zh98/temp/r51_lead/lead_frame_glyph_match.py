# -*- coding: utf-8 -*-
r"""lead_frame_glyph_match.py — 在**已有实机帧**里搜"与字库模板逐像素相同"的 16x16 字形

思路: 引擎按 16x16 采样窗把字形 1:1 画到屏幕上 => 只要屏幕上出现与模板**逐像素相同**的
      16x16 墨点图案, 就证明"引擎确实把该字画成了正确字形"(无需新跑导航)。
用法: python lead_frame_glyph_match.py <帧目录> [<帧目录> ...]
"""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import glyph_geometry as G                              # noqa: E402

# 28 个单字节汉字 (码位 0x80..0x9B)
CHARS = list('《》享伞促凝双吸壳套尖履巨拆捕旋池热燃牛牲牺猪玻璃磁磅稳')
print('目标字: %d 个' % len(CHARS))

T = G.Templates()
tpls = {}
for ch in CHARS:
    t = T.get(ch)
    if t is not None:
        tpls[ch] = t.astype(np.uint8)
print('取到模板: %d 个; 墨点数: %s' % (len(tpls), {c: int(v.sum()) for c, v in list(tpls.items())[:6]}))


def match_frame(g):
    """在灰度图 g 里找与任一模板逐像素相同的 16x16 窗口 (二分图 = 墨/非墨)。

    ★ 两种极性都试: 深底浅字 / 浅底深字。
    """
    out = []
    for thresh_invert in (False, True):
        ink = ((g >= 128) if thresh_invert else (g < 128)).astype(np.uint8)
        h, w = ink.shape
        hits = []
        # 用积分图快速筛"墨点数相同"的窗口
        ii = np.zeros((h + 1, w + 1), dtype=np.int32)
        ii[1:, 1:] = np.cumsum(np.cumsum(ink, 0), 1)
        for ch, t in tpls.items():
            n = int(t.sum())
            for y in range(0, h - 16 + 1):
                row = ii[y + 16, :] - ii[y, :]
                cnt = row[16:] - row[:-16]
                for x in np.nonzero(cnt == n)[0]:
                    if np.array_equal(ink[y:y + 16, x:x + 16], t):
                        hits.append((ch, int(x), int(y), 'invert' if thresh_invert else 'normal'))
        out.extend(hits)
    return out


dirs = sys.argv[1:]
total = {}
for d in dirs:
    d = os.path.join(REPO, d) if not os.path.isabs(d) else d
    if not os.path.isdir(d):
        print('跳过(不存在): %s' % d)
        continue
    fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
    print()
    print('=' * 70)
    print('%s : %d 帧' % (os.path.relpath(d, REPO), len(fs)))
    found = {}
    for f in fs:
        im = Image.open(os.path.join(d, f)).convert('L')
        g = np.asarray(im)
        for ch, x, y in match_frame(g):
            found.setdefault(ch, []).append((f, x, y))
    if not found:
        print('  **没有**任何目标字形与模板逐像素相同')
    else:
        print('  ★ 命中 %d 个目标字:' % len(found))
        for ch in CHARS:
            if ch in found:
                hits = found[ch]
                print('    %s : %d 次  例: %s @(%d,%d)' % (ch, len(hits), hits[0][0], hits[0][1], hits[0][2]))
                total.setdefault(ch, []).append((os.path.basename(d), len(hits)))
print()
print('=' * 70)
print('汇总: 在已有实机帧里命中 %d / %d 个目标字' % (len(total), len(CHARS)))
if total:
    print('  命中的字:', ''.join(c for c in CHARS if c in total))
    print('  未命中的字:', ''.join(c for c in CHARS if c not in total))
