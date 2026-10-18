# -*- coding: utf-8 -*-
r"""lead_frame_glyph_tol.py — 容差版: 在已有实机帧里搜"与模板高度一致"的 16x16 字形

精确匹配会被 GS 双线性过滤破坏 => 改用 XOR 容差 (>=88% 一致, 允许 ±2 平移)。
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

CHARS = list('《》享伞促凝双吸壳套尖履巨拆捕旋池热燃牛牲牺猪玻璃磁磅稳')
T = G.Templates()
tpls = {c: T.get(c).astype(np.uint8) for c in CHARS if T.get(c) is not None}
THRESH = 0.88


def best_match(g):
    """返回 {字: (一致率, x, y, 极性)} 中每个字的最佳命中 (只保留 >= THRESH)。"""
    res = {}
    for inv in (False, True):
        ink = ((g >= 128) if inv else (g < 128)).astype(np.uint8)
        h, w = ink.shape
        s = np.lib.stride_tricks.sliding_window_view(ink, (16, 16))
        tot = s.sum(axis=(2, 3))
        for ch, t in tpls.items():
            ov = np.tensordot(s, t, axes=([2, 3], [0, 1]))
            xor = tot + int(t.sum()) - 2 * ov
            agree = 1.0 - xor / 256.0
            for dy in (-2, -1, 0, 1, 2):
                for dx in (-2, -1, 0, 1, 2):
                    if dy < 0 or dx < 0:
                        continue
                    a = agree[dy:agree.shape[0] - (2 - dy) if dy else agree.shape[0],
                              dx:agree.shape[1] - (2 - dx) if dx else agree.shape[1]]
                    if a.size == 0:
                        continue
                    iy, ix = np.unravel_index(int(np.argmax(a)), a.shape)
                    v = float(a[iy, ix])
                    key = (ch, inv)
                    if v >= THRESH and v > res.get(key, (0,))[0]:
                        res[key] = (v, int(ix), int(iy), inv)
    return res


dirs = sys.argv[1:]
allhits = {}
for d in dirs:
    d = d if os.path.isabs(d) else os.path.join(REPO, d)
    if not os.path.isdir(d):
        continue
    fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
    print('%-58s %4d 帧' % (os.path.relpath(d, REPO)[-58:], len(fs)))
    for f in fs:
        g = np.asarray(Image.open(os.path.join(d, f)).convert('L'))
        for (ch, inv), (v, x, y, _i) in best_match(g).items():
            allhits.setdefault(ch, []).append((os.path.basename(d), f, round(v, 4), x, y, inv))
print()
print('=' * 74)
print('容差 >= %.0f%% 的命中: %d / %d 个目标字' % (THRESH * 100, len(allhits), len(CHARS)))
for ch in CHARS:
    if ch in allhits:
        hs = allhits[ch]
        b = max(hs, key=lambda z: z[2])
        print('  %s : %d 次, 最佳一致率 %.4f  @ %s/%s (%d,%d) invert=%s'
              % (ch, len(hs), b[2], b[0], b[1], b[3], b[4], b[5]))
if allhits:
    print('  命中字集:', ''.join(c for c in CHARS if c in allhits))
    print('  未命中  :', ''.join(c for c in CHARS if c not in allhits))
