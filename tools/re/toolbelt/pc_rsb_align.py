#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_align.py -- 判定 .rsb 表面起点: 头后紧跟 vs 文件尾对齐 (round77 任务 A1/C)"""
import io
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")

CASES = [
    ("Data/Shell/Art/Chinese0.rsb", 512, 512, 16, [28, 32, 93], "cn0"),
    ("Data/Shell/Art/Chinese2.rsb", 512, 512, 16, [28, 32, 93], "cn2"),
    ("Data/Shell/Art/gb1600.rsb", 512, 512, 16, [28, 32, 109], "gb1600"),
    ("Data/Shell/Art/gb1200.rsb", 512, 512, 16, [28, 32, 109], "gb1200"),
    ("Data/Shell/Art/new_font_revised.rsb", 256, 256, 32, [28, 32, 109], "nfr"),
]


def score(img):
    """格网对齐分数: 上半区行投影的周期纯度 (越大越像整齐的字模图集)"""
    ink = (img > 8).astype(np.int64)
    rows = ink.sum(1).astype(np.float64)
    if rows.sum() == 0:
        return 0.0
    # 找一个周期 p 让行投影尽可能"周期化" — 用自相关最大值
    p = rows - rows.mean()
    best = 0.0
    for lag in range(8, 40):
        best = max(best, float((p[:-lag] * p[lag:]).mean()))
    # 归一化
    return best / max(float((p * p).mean()), 1e-9)


def main():
    L = []
    A = L.append
    for rel, w, h, bpp, offs, tag in CASES:
        b = open(os.path.join(PC, rel), "rb").read()
        need = w * h * bpp // 8
        A("\n### %s  size=%d need=%d" % (rel, len(b), need))
        for off in offs:
            if off + need > len(b):
                A("  off=%-4d 越界" % off)
                continue
            if bpp == 16:
                img = np.frombuffer(b[off:off + need], "<u2").reshape(h, w)
                plane = (img & 0xFF).astype(np.uint8)
            elif bpp == 32:
                a = np.frombuffer(b[off:off + need], np.uint8).reshape(h, w, 4)
                ch = max(range(4), key=lambda k: float(a[:, :, k].std()))
                plane = a[:, :, ch]
            else:
                continue
            s = score(plane)
            A("  off=%-4d 格网纯净度=%.4f  墨占比=%.4f" %
              (off, s, float((plane > 8).mean())))
            Image.fromarray(plane, "L").save(
                os.path.join(OUT, "%s_off%d.png" % (tag, off)))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_rsb_align.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
