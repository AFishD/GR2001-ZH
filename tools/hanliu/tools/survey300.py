# [hanliu 收编] 原件: C:/gr_build/tmp/zh8b/survey300.py (逐字复制)。原件保留于原处未动。
# -*- coding: utf-8 -*-
"""survey300.py — 双盘同 nav 快照回归普查 (参照 zh7q 方法族)
用法: python survey300.py <dumpA(基准)> <dumpB(对照)> [样本数=300] [json_out]
对随机 N 个共同快照逐帧 diff; 旗标 = 指定动画区之外存在 >8 灰阶差异的像素。
"""
import os, random, json, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
A, B = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 300
JOUT = sys.argv[4] if len(sys.argv) > 4 else None
LOGO = (20, 0, 110, 52)   # 动画 logo 区 (左上; 本项目菜单页唯一已知动画差异源)
fa = {f for f in os.listdir(A) if f.startswith("snap_")}
fb = {f for f in os.listdir(B) if f.startswith("snap_")}
common = sorted(fa & fb)
rng = random.Random(74)
sample = rng.sample(common, min(N, len(common)))
flagged, zero, logo_only = [], 0, 0
for f in sample:
    a = np.asarray(Image.open(os.path.join(A, f)).convert("RGB"), dtype=np.int16)
    b = np.asarray(Image.open(os.path.join(B, f)).convert("RGB"), dtype=np.int16)
    d = np.abs(a - b).max(axis=2)
    m = d > 8
    n = int(m.sum())
    if n == 0:
        zero += 1; continue
    ys, xs = np.where(m)
    keep = ~((xs >= LOGO[0]) & (xs < LOGO[2]) & (ys >= LOGO[1]) & (ys < LOGO[3]))
    if not keep.any():
        logo_only += 1; continue
    xk, yk = xs[keep], ys[keep]
    flagged.append((f, int(keep.sum()), (int(xk.min()), int(yk.min()), int(xk.max()), int(yk.max()))))
print("普查 %d 帧: 全零差=%d 仅动画区差=%d 旗标=%d" % (len(sample), zero, logo_only, len(flagged)))
for f, n, bb in flagged[:30]:
    print("  FLAG %s out=%d bbox=%s" % (f, n, bb))
if JOUT:
    json.dump({"sample": len(sample), "zero": zero, "logo_only": logo_only,
               "flagged": flagged}, open(JOUT, "w"), indent=1)
