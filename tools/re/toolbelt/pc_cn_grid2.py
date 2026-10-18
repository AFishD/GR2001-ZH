#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_grid2.py -- 在正确的 512x512 16bpp 视图上测 Chinese*.rsb 的格网 pitch (round77)"""
import io
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
ART = os.path.join(PC, "Data", "Shell", "Art")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def load(name):
    b = open(os.path.join(ART, name), "rb").read()
    px = 512 * 512 * 2
    off = len(b) - px
    return np.frombuffer(b[off:off + px], "<u2").reshape(512, 512)


def best_grid(mask, pitch, axis):
    """返回 (边界墨占比, 最佳相位)"""
    n = 512
    proj = mask.sum(axis=1 - axis).astype(np.float64) if axis == 0 else \
        mask.sum(axis=0).astype(np.float64)
    tot = proj.sum()
    best = (9e9, -1)
    for ph in range(pitch):
        idx = np.arange(ph, n, pitch)
        if len(idx) == 0:
            continue
        v = proj[idx].mean() / max(proj.mean(), 1e-9)
        if v < best[0]:
            best = (v, ph)
    return best


def main():
    L = []
    A = L.append
    A("== 512x512 16bpp 视图下的格网 (lo 字节为墨) ==")
    A("  u16==0xffff 视为墨 (gb 系) / u16!=0 视为墨 (Chinese 系)")
    for name in ["Chinese0.rsb", "Chinese1.rsb", "Chinese2.rsb",
                 "Chinese3.rsb", "Chinese4.rsb",
                 "gb1200.rsb", "gb1600.rsb", "gb1601.rsb",
                 "gb2400.rsb", "gb2401.rsb", "gb2402.rsb"]:
        u = load(name)
        m_all = (u != 0)
        m_w = (u == 0xFFFF)
        A("\n### %s  (u16!=0: %d,  u16==0xffff: %d)" %
          (name, int(m_all.sum()), int(m_w.sum())))
        for tag, mask in (("any!=0", m_all), ("==ffff", m_w)):
            res = []
            for p in range(8, 33):
                vc, pc = best_grid(mask, p, 0)
                vr, pr = best_grid(mask, p, 1)
                res.append((p, vc, pc, vr, pr))
            # 找列方向最小
            res_c = sorted(res, key=lambda t: t[1])[:4]
            res_r = sorted(res, key=lambda t: t[3])[:4]
            A("  [%s] 列边界最小: %s" %
              (tag, ", ".join("p%d(ph%d)=%.3f" % (p, ph, v)
                              for p, v, ph, _, _ in res_c)))
            A("  [%s] 行边界最小: %s" %
              (tag, ", ".join("p%d(ph%d)=%.3f" % (p, ph, v)
                              for p, _, _, v, ph in res_r)))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn_grid2.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
