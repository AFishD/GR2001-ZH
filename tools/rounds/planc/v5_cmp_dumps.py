# -*- coding: utf-8 -*-
r"""v5_cmp_dumps.py <dumpA> <dumpB> [out.png] — 逐帧对比两个转储目录 (同导航)。
只比两边都有的帧; 输出相同/不同的帧号列表, 并对差异帧存并排图。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                     # noqa: E402
from PIL import Image                                  # noqa: E402

A, B = sys.argv[1], sys.argv[2]
OUT = sys.argv[3] if len(sys.argv) > 3 else None


def frames(d):
    out = {}
    for fn in os.listdir(d):
        if fn.startswith('snap_f') and fn.endswith('.png'):
            out[int(fn[6:14])] = os.path.join(d, fn)
    return out


fa, fb = frames(A), frames(B)
common = sorted(set(fa) & set(fb))
print('A 帧 %d, B 帧 %d, 共有 %d' % (len(fa), len(fb), len(common)))
same, diff = [], []
for f in common:
    ia = np.asarray(Image.open(fa[f]).convert('RGB'), dtype=np.int16)
    ib = np.asarray(Image.open(fb[f]).convert('RGB'), dtype=np.int16)
    if ia.shape != ib.shape:
        diff.append((f, -1))
        continue
    n = int((np.abs(ia - ib).max(axis=2) > 0).sum())
    (same if n == 0 else diff).append((f, n))
print('逐像素相同 %d 帧; 不同 %d 帧' % (len(same), len(diff)))
if diff:
    print('  不同的帧 (帧号: 不同像素数):')
    for f, n in diff[:40]:
        print('    F%-7d %s' % (f, n if n >= 0 else '尺寸不同'))
print('  相同帧号: %s%s' % (same[:12], ' …' if len(same) > 12 else ''))
if OUT and diff:
    f0 = diff[0][0]
    ia = Image.open(fa[f0]).convert('RGB')
    ib = Image.open(fb[f0]).convert('RGB')
    w, h = ia.size
    canvas = Image.new('RGB', (w * 2 + 8, h), (32, 32, 32))
    canvas.paste(ia, (0, 0))
    canvas.paste(ib, (w + 8, 0))
    canvas.save(OUT)
    print('  并排图 (F%d: 左=A 右=B) → %s' % (f0, OUT))
