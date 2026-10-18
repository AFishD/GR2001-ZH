# -*- coding: utf-8 -*-
r"""m9_precheck.py — round47 ⑨: 用「预检副本」判定记录格被污染的像素。

patch_zh93_font_ext.py 的写盘口径:
  · 引擎格 = flat→引擎 换算后的记录 (u0,v0) —— 引擎真正采样处;
  · 预检格 = 把 (u0,v0) 当 **flat 坐标** 得到的那一格 —— 同一张字形位图的**第二份**副本,
    引擎不采样 (只给 tcslib 预检看)。
⇒ 两份副本应当**逐像素相同**; 不同处 = 被别的东西盖过 = 污染, 而且预检副本就是**真值**。
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, default_rects   # noqa: E402
import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402
import patch_zh94_glyph_align as P                                       # noqa: E402

cs = tcslib.Charset()
rev = dict((b, c) for c, b in cs.enc_single.items())

out = {}
for ver in ('GR_ZH93', 'GR_ZH94'):
    A = load(ver)
    a = A['eng']
    segs = A['segs']
    dflt = default_rects(A['faces'])
    print('=' * 78)
    print('%s: 引擎格 (u0,v0) vs 预检格 flat_to_engine(u0,v0)' % ver)
    stats = collections.Counter()
    detail = []
    for code in range(0x21, 0xFF):
        if code not in dflt:
            continue
        ch = rev.get(code)
        u0, v0, u1, v1 = dflt[code]
        w, h = u1 - u0, v1 - v0
        if not (w and h):
            continue
        try:
            px, py = P.flat_to_engine(segs, u0, v0)
        except Exception as e:                                          # noqa: BLE001
            px, py = None, None
        eng = a[v0:v0 + h, u0:u0 + w]
        if px is None or px + w > W or py + h > H or py < 0:
            stats['预检格越界'] += 1
            detail.append((code, ch, u0, v0, w, h, None, None))
            continue
        pre = a[py:py + h, px:px + w]
        d = int((eng != pre).sum())
        stats[d] += 1
        if d:
            ys, xs = np.where(eng != pre)
            detail.append((code, ch, u0, v0, w, h, (px, py), d, int(ys.min()), int(ys.max()),
                           int(xs.min()), int(xs.max())))
        else:
            detail.append((code, ch, u0, v0, w, h, (px, py), 0, None, None, None, None))
    print('  两份副本差像素数分布: %s' % stats.most_common(12))
    print('  预检格坐标 = flat_to_engine(u0,v0)')
    print('  --- 有差异的 (只有单字节码会走这条路) ---')
    for t in detail:
        if len(t) >= 8 and t[7]:
            print('    0x%02X %-3s 记录(%4d,%3d) %2dx%2d 预检(%4d,%3d) 差=%2d  '
                  '行 %d..%d 列 %d..%d'
                  % (t[0], t[1] or '', t[2], t[3], t[4], t[5], t[6][0], t[6][1], t[7],
                     t[8], t[9], t[10], t[11]))
    out[ver] = [dict(code=t[0], ch=t[1], u0=t[2], v0=t[3], w=t[4], h=t[5],
                     pre=list(t[6]) if t[6] else None, diff=t[7] if len(t) > 7 else None,
                     rows=[t[8], t[9]] if len(t) > 8 and t[8] is not None else None,
                     cols=[t[10], t[11]] if len(t) > 10 and t[10] is not None else None)
                 for t in detail]

io.open(os.path.join(HERE, 'm9_precheck.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps(out, ensure_ascii=False, indent=1) + '\n')
print()
print('[out] → m9_precheck.json')
