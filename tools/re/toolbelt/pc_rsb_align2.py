#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_align2.py -- 用「格线整行零墨」硬判据定 .rsb 表面起点 (round77)"""
import io
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")

CASES = [
    ("Data/Shell/Art/gb1600.rsb", 512, 512, 16, 16),
    ("Data/Shell/Art/gb1601.rsb", 512, 512, 16, 16),
    ("Data/Shell/Art/gb1200.rsb", 512, 512, 16, 12),
    ("Data/Shell/Art/gb2400.rsb", 512, 512, 16, 24),
    ("Data/Shell/Art/Chinese1.rsb", 512, 512, 16, 16),
    ("Data/Shell/Art/Chinese2.rsb", 512, 512, 16, 24),
]


def main():
    L = []
    A = L.append
    for rel, w, h, bpp, pitch in CASES:
        b = open(os.path.join(PC, rel), "rb").read()
        need = w * h * bpp // 8
        A("\n### %s size=%d need=%d  (pitch=%d)" % (rel, len(b), need, pitch))
        for off in range(20, 40):
            if off + need > len(b):
                break
            u = np.frombuffer(b[off:off + need], "<u2").reshape(h, w)
            plane = (u & 0xFF)
            cols = (plane > 8).sum(0)
            # 该 pitch 下最优相位 (列格线)
            top = sorted(((int(cols[np.arange(ph, w, pitch)].sum()), ph)
                          for ph in range(pitch)))[:3]
            best = top[0]
            A("  off=%-3d 列格线最小墨=%5d (相位 %d)  top3=%s" %
              (off, best[0], best[1], top))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_rsb_align2.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
