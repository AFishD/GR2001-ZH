# -*- coding: utf-8 -*-
"""r51 A/B: 逐帧逐像素比较两次实机转储 (同名帧)。用法: ab_frames.py <A目录> <B目录> [--out JSON]"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np
from PIL import Image

A, B = sys.argv[1], sys.argv[2]
out = None
if '--out' in sys.argv:
    out = sys.argv[sys.argv.index('--out') + 1]

fa = {f for f in os.listdir(A) if f.startswith('snap_') and f.endswith('.png')}
fb = {f for f in os.listdir(B) if f.startswith('snap_') and f.endswith('.png')}
both = sorted(fa & fb)
only_a = sorted(fa - fb)
only_b = sorted(fb - fa)
print('A=%s (%d 帧)  B=%s (%d 帧)  同名 %d' % (A, len(fa), B, len(fb), len(both)))

rows, ndiff = [], 0
for f in both:
    a = np.asarray(Image.open(os.path.join(A, f)).convert('RGB')).astype(np.int16)
    b = np.asarray(Image.open(os.path.join(B, f)).convert('RGB')).astype(np.int16)
    if a.shape != b.shape:
        rows.append(dict(frame=f, shape=[list(a.shape), list(b.shape)], diff=-1))
        ndiff += 1
        continue
    d = np.abs(a - b).max(axis=2)
    n = int((d > 0).sum())
    if n:
        ndiff += 1
        ys, xs = np.where(d > 0)
        rows.append(dict(frame=f, diff_px=n, max_delta=int(d.max()),
                         bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]))
print('逐像素完全相同的帧: %d / %d' % (len(both) - ndiff, len(both)))
print('有差异的帧: %d' % ndiff)
for r in rows[:40]:
    print('   %s  diff=%s maxΔ=%s bbox=%s' % (r['frame'], r.get('diff_px'), r.get('max_delta'),
                                              r.get('bbox')))
if out:
    io.open(out, 'w', encoding='utf-8', newline='\n').write(json.dumps(
        dict(A=A, B=B, frames_common=len(both), identical=len(both) - ndiff, differing=ndiff,
             only_in_A=only_a[:20], only_in_B=only_b[:20], rows=rows),
        ensure_ascii=False, indent=1) + '\n')
    print('[报告] %s' % out)
