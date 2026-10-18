#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_tga2rsb.py -- 用 TGA 源码反证 .rsb 的表面偏移与像素格式 (round77 任务 A1/C)

PC 的 RSB 是 TGA 的引擎缓存 (docs/han_v2/PC_FONT_MECHANISM.md §3.3)。
把 GB1600.TGA 转成 R5G6B5, 在 gb1600.rsb 里定位, 即可定出表面偏移与头部长度。
"""
import io
import os
import struct

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ART = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "Data", "Shell", "Art")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def read_tga(path):
    b = open(path, "rb").read()
    idlen, cmaptype, imgtype = b[0], b[1], b[2]
    cmap = struct.unpack_from("<HHB", b, 3)
    x0, y0, w, h, bpp, desc = struct.unpack_from("<HHHHBB", b, 8)
    off = 18 + idlen
    px = b[off:]
    return dict(raw=b, idlen=idlen, imgtype=imgtype, cmap=cmap, w=w, h=h,
                bpp=bpp, desc=desc, off=off, px=px)


def main():
    L = []
    A = L.append
    for stem in ("GB1600", "GB1601", "GB2400", "GB1200"):
        tga = os.path.join(ART, stem + ".tga")
        rsb = os.path.join(ART, stem.lower() + ".rsb")
        if not (os.path.exists(tga) and os.path.exists(rsb)):
            A("MISSING %s / %s" % (tga, rsb))
            continue
        t = read_tga(tga)
        rb = open(rsb, "rb").read()
        A("=" * 84)
        A("### %s.tga size=%d  idlen=%d imgtype=%d cmap=%s %dx%d %dbpp desc=0x%02x dataoff=%d" %
          (stem, len(t["raw"]), t["idlen"], t["imgtype"], t["cmap"],
           t["w"], t["h"], t["bpp"], t["desc"], t["off"]))
        A("    %s.rsb size=%d" % (stem, len(rb)))
        if t["bpp"] != 32:
            A("    (非 32bpp, 跳过)")
            continue
        a = np.frombuffer(t["px"][:t["w"] * t["h"] * 4], np.uint8).reshape(
            t["h"], t["w"], 4)
        # TGA 32bpp 默认 BGRA
        B, G, R, Al = (a[:, :, i].astype(np.uint16) for i in range(4))
        r5 = (R >> 3) << 11
        g6 = (G >> 2) << 5
        b5 = (B >> 3)
        v = (r5 | g6 | b5).astype("<u2")
        # 顶行对齐: desc bit5=0 → bottom-up
        for tag, arr in (("topdown", v),
                         ("bottomup", v[::-1])):
            flat = arr.tobytes()
            idx = rb.find(flat[:4096])
            A("    %-9s 前 4096B 在 rsb 中的位置 = %s  (期望 %d)" %
              (tag, ("0x%x" % idx) if idx >= 0 else "未找到", len(rb) - len(flat)))
            if idx >= 0:
                A("      表面偏移 = %d, 头部长度 = %d, 尾部 = %d" %
                  (idx, idx, len(rb) - idx - len(flat)))
                full = rb.find(flat)
                A("      整幅匹配位置 = %s" % (("0x%x" % full) if full >= 0 else "未找到"))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_tga2rsb.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
