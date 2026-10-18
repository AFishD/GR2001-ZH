#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_render.py -- 把 PC .rsb 当 8bpp 表面渲染出来看 (round77 任务 A1)

用法:
  python tools/re/toolbelt/pc_rsb_render.py <relpath> <pixel_offset> <w> <h> <outname> [--rgb]
输出 -> work/builds/GR_ZH98/temp/r77/<outname>.png
"""
import io
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)


def render(rel, off, w, h, name, scale=1):
    b = open(os.path.join(PC, rel), "rb").read()
    px = b[off:off + w * h]
    print("%s: file=%d off=%d need=%d got=%d" % (rel, len(b), off, w * h, len(px)))
    if len(px) < w * h:
        px = px + b"\x00" * (w * h - len(px))
    img = Image.frombytes("L", (w, h), px)
    if scale != 1:
        img = img.resize((w * scale, h * scale), Image.NEAREST)
    p = os.path.join(OUT, name + ".png")
    img.save(p)
    print("  ->", p)
    # 统计
    hist = img.histogram() if scale == 1 else None
    if hist:
        print("  nonzero rows:", sum(1 for y in range(h)
                                     if any(px[y * w + x] for x in range(w))))
    return p


if __name__ == "__main__":
    a = sys.argv[1:]
    render(a[0], int(a[1]), int(a[2]), int(a[3]), a[4],
           int(a[5]) if len(a) > 5 else 1)
