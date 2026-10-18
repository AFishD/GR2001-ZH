# -*- coding: utf-8 -*-
r"""lead_shift28.py — 精确算出这 28 格的错位量: 允许 ±1/±2 像素平移后与全部模板比 IoU"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D            # noqa: E402
import glyph_geometry as G       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')
atlas = D.load_font(ISO)['atlas']
W, H = atlas['w'], atlas['h']
gray = np.frombuffer(D.atlas_gray(atlas, view='engine'), dtype=np.uint8).reshape(H, W)
ink = gray < 128
tpl = G.Templates()

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
code2ch = {v: k for k, v in cs['codes'].items()}
cands = list(cs['pair_of'].keys()) + [c for c in cs['codes'] if not c.isspace()]
tpl_cache = {}
for ch in cands:
    t = tpl.get(ch)
    if t is not None:
        tpl_cache[ch] = t
print('可用模板 %d 个' % len(tpl_cache))


def best_iou(cell, t, maxs=2):
    """cell 与 t 在 ±maxs 像素平移下的最大 IoU"""
    best = 0.0
    for dy in range(-maxs, maxs + 1):
        for dx in range(-maxs, maxs + 1):
            c = np.roll(np.roll(cell, dy, axis=0), dx, axis=1)
            inter = int(np.logical_and(c, t).sum())
            union = int(np.logical_or(c, t).sum())
            if union:
                best = max(best, inter / union)
    return best


print()
print('%-4s %-5s  %-8s %-8s %-6s  %s' % ('字', '码', '盘上→最像', 'IoU', '错位', '结论'))
shift_list = []
for i in range(28):
    code = 0x80 + i
    ch = code2ch.get(code, '?')
    x = i * 16
    cell = ink[482:498, x:x + 16]
    scored = []
    for c, t in tpl_cache.items():
        scored.append((best_iou(cell, t), c))
    scored.sort(reverse=True)
    top = scored[0]
    # 精确错位: 用最佳匹配字反查其码位
    b2 = cs['codes'].get(top[1])
    shift = (b2 - code) if isinstance(b2, int) else None
    shift_list.append(shift)
    print('%-4s %02X    %-8s %.3f  %-6s  %s'
          % (ch, code, top[1], top[0], ('%+d' % shift) if shift is not None else '?',
             '✓ 正确' if top[1] == ch else '✗ 画成别的字'))
print()
ok = sum(1 for i in range(28) if (lambda c: True)(0) and False)
print('错位量分布:', sorted(set(s for s in shift_list if s is not None)))
