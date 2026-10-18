#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_font_profile.py -- 打印 Chinese0 行/列墨迹投影, 精确找格网 (round77)"""
import io
import os

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def main():
    b = open(os.path.join(PC, "Data", "Shell", "Art", "Chinese0.rsb"), "rb").read()
    px = np.frombuffer(b[93:93 + 524288], np.uint8)
    a = px.reshape(512, 1024)
    ink = (a > 8).astype(np.int32)
    rows = ink.sum(1)
    cols = ink.sum(0)

    L = []
    A = L.append
    A("== 8bpp 1024x512 行投影 (每行墨像素数) ==")
    for y in range(0, 512):
        A("  y=%3d  %4d" % (y, rows[y]))
    A("\n== 列投影 ==")
    for x in range(0, 1024):
        A("  x=%4d  %4d" % (x, cols[x]))

    # 行投影的"低频结构": 每 4 行求和
    A("\n== 行投影 4 行块 ==")
    for y in range(0, 512, 4):
        A("  y=%3d..%3d  %5d" % (y, y + 3, rows[y:y + 4].sum()))

    # 空行/低墨行
    A("\n== 行墨 < 50 的行 ==")
    A("  " + " ".join(str(y) for y in range(512) if rows[y] < 50))
    A("\n== 列墨 < 20 的列 ==")
    A("  " + " ".join(str(x) for x in range(1024) if cols[x] < 20))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn0_profile.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written")


if __name__ == "__main__":
    main()
