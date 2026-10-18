# -*- coding: utf-8 -*-
r"""m1_phi.py — 从 b20_map.json (全图集模板匹配结果) 反解每行真实相位 PHI, 并给出占格图。

只读分析, 不写任何产物 (除 stdout)。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SRC = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'b20_map.json')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')

M = json.load(open(SRC, encoding='utf-8'))
print('b20_map.json keys:', list(M.keys()))
res = M['map']
js = json.load(open(CS, encoding='utf-8'))


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


rows = {}
for ch, (b0, b1) in js['pair_of'].items():
    if ch not in res:
        continue
    x, y, sc = res[ch][0], res[ch][1], res[ch][2]
    if sc < 250:
        continue
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    rows.setdefault(R, []).append((C, x // 16, y, ch, sc))

print()
print('== 每行实测相位 ==')
print('  R   n   y(实测)      (col-C)mod64 分布        公式 yrow(R)')
for R in sorted(rows):
    v = sorted(rows[R])
    offs = {}
    for C, col, y, ch, sc in v:
        d = (col - C) % 64
        offs[d] = offs.get(d, 0) + 1
    yy = sorted({y for _C, _c, y, _ch, _s in v})
    top = sorted(offs.items(), key=lambda kv: -kv[1])[:4]
    print('  %2d %4d  %-12s  %-28s  %d'
          % (R, len(v), str(yy), ' '.join('%d x%d' % k for k in top), yrow(R)))

print()
print('== slot%(62) vs col 线性检查 (每行取众数相位) ==')
for R in sorted(rows):
    v = sorted(rows[R])
    offs = {}
    for C, col, y, ch, sc in v:
        offs[(col - C) % 64] = offs.get((col - C) % 64, 0) + 1
    phi = max(offs.items(), key=lambda kv: kv[1])[0]
    bad = [(C, col, ch) for C, col, y, ch, sc in v if col != (C + phi) % 64]
    print('  R=%2d phi=%2d 命中 %d/%d  例外 %s' % (R, phi, len(v) - len(bad), len(v), bad[:6]))
