#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_font_cc.py -- 连通域分析定 Chinese*.rsb 的真实格网 (round77 任务 A1/A2/A3)"""
import collections
import io
import os

import numpy as np
from PIL import Image

try:
    from scipy import ndimage
    HAVE = True
except Exception:
    HAVE = False

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def main():
    print("scipy =", HAVE)
    b = open(os.path.join(PC, "Data", "Shell", "Art", "Chinese0.rsb"), "rb").read()
    px = b[93:93 + 524288]
    a = np.frombuffer(px, np.uint8).reshape(512, 1024)
    ink = a > 8

    L = []
    A = L.append
    A("== Chinese0.rsb 连通域 ==")
    lab, n = ndimage.label(ink)
    A("连通域数 = %d" % n)
    sl = ndimage.find_objects(lab)
    ws, hs, xs, ys = [], [], [], []
    for s in sl:
        h = s[0].stop - s[0].start
        w = s[1].stop - s[1].start
        ws.append(w)
        hs.append(h)
        xs.append(s[1].start)
        ys.append(s[0].start)
    ws = np.array(ws)
    hs = np.array(hs)
    xs = np.array(xs)
    ys = np.array(ys)
    A("bbox 宽 分布: %s" % sorted(collections.Counter(ws.tolist()).items(),
                                   key=lambda x: -x[1])[:12])
    A("bbox 高 分布: %s" % sorted(collections.Counter(hs.tolist()).items(),
                                   key=lambda x: -x[1])[:12])
    A("bbox 宽 分位: min=%d p50=%d p90=%d max=%d" %
      (ws.min(), int(np.percentile(ws, 50)), int(np.percentile(ws, 90)), ws.max()))
    A("bbox 高 分位: min=%d p50=%d p90=%d max=%d" %
      (hs.min(), int(np.percentile(hs, 50)), int(np.percentile(hs, 90)), hs.max()))

    # 只看大连通域(可能是整字)
    big = (ws >= 10) & (hs >= 10)
    A("大域(>=10x10) = %d" % big.sum())
    # 用大域的 x 起点聚类, 找列 pitch
    bx = np.sort(np.unique(xs[big]))
    A("大域 x 起点 (前 80): %s" % bx[:80].tolist())
    d = np.diff(bx)
    A("x 起点间隔直方图: %s" %
      sorted(collections.Counter(d.tolist()).items(), key=lambda x: -x[1])[:15])
    by = np.sort(np.unique(ys[big]))
    A("大域 y 起点 (前 60): %s" % by[:60].tolist())
    dy = np.diff(by)
    A("y 起点间隔直方图: %s" %
      sorted(collections.Counter(dy.tolist()).items(), key=lambda x: -x[1])[:15])

    # 行/列墨迹投影的"格子边界"搜索: 对每个 pitch, 求边界线墨量的最小相位
    A("\n== 边界线墨量最小化搜索 (pitch, 最佳相位, 边界墨/总墨) ==")
    cols = ink.sum(0).astype(np.float64)
    rows = ink.sum(1).astype(np.float64)
    for pitch in (12, 14, 16, 18, 20, 21, 22, 24, 25, 26, 28, 30, 32, 36, 40, 42, 48, 64):
        best = None
        for ph in range(pitch):
            idx = np.arange(ph, 1024, pitch)
            v = cols[idx].sum() / max(cols.sum(), 1) * (1024.0 / len(idx))
            if best is None or v < best[0]:
                best = (v, ph, len(idx))
        # 归一化: 平均每列墨量基准
        base = cols.mean()
        A("  cols pitch=%-3d 相位=%-3d 线数=%-3d 边界列均墨=%.1f (全局均墨 %.1f)" %
          (pitch, best[1], best[2], best[0] * base / (1024.0 / best[2]) / base * base, base))
        bestr = None
        for ph in range(pitch):
            idx = np.arange(ph, 512, pitch)
            v = rows[idx].sum() / max(rows.sum(), 1) * (512.0 / len(idx))
            if bestr is None or v < bestr[0]:
                bestr = (v, ph, len(idx))
        A("  rows pitch=%-3d 相位=%-3d 线数=%-3d 边界行份额=%.4f" %
          (pitch, bestr[1], bestr[2], bestr[0]))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn_font_cc.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
