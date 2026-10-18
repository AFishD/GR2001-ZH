#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_final.py -- 用已证实的 {43B 头}{表面}{尾} 模型渲染 PC .rsb (round77)

模型 (由 GB*.tga -> GB*.rsb 逐字节定位反证):
  0x00  {u32 mode}
  0x04  {u32 w}
  0x08  {u32 h}
  模式 4/5/6: 0x0c {u32 p0}{p1}{p2}{p3}  (LE)
  模式 9:     0x10 {u32 p0}{p1}{p2}{p3}  (BE)   [0x0c 多一个 u32]
  bpp = p0+p1+p2+p3
  0x2B (43) 起 w*h*bpp/8 字节 = 表面 (u16 LE = R5G6B5 或 32bpp BGRA)
  尾部: mode4=38 / mode5=46 / mode6=50 / mode9=66 字节
"""
import io
import os
import struct

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ART = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "Data", "Shell", "Art")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
SURF = 43


def parse(path):
    b = open(path, "rb").read()
    mode, w, h = struct.unpack_from("<3I", b, 0)
    if mode == 9:
        p = [struct.unpack_from(">I", b, 0x10 + 4 * i)[0] for i in range(4)]
    else:
        p = [struct.unpack_from("<I", b, 0x0C + 4 * i)[0] for i in range(4)]
    bpp = sum(p)
    need = w * h * bpp // 8
    tail = len(b) - SURF - need
    return b, mode, w, h, p, bpp, need, tail


def main():
    L = []
    A = L.append
    A("== 模型自检: filesize == 43 + w*h*bpp/8 + tail ==")
    names = sorted(f for f in os.listdir(ART) if f.lower().endswith(".rsb"))
    bad = 0
    for n in names:
        b, mode, w, h, p, bpp, need, tail = parse(os.path.join(ART, n))
        ok = tail >= 0
        if not ok:
            bad += 1
        A("  %-26s mode=%d %4dx%-4d p=%-18s bpp=%-3d surface=%-8d tail=%-4d %s" %
          (n, mode, w, h, str(p), bpp, need, tail, "OK" if ok else "!!"))
    A("  自检: %d 个文件, 不符 %d 个" % (len(names), bad))

    # 渲染 new_font_revised (RSFontMgr 的拉丁图集)
    for nm, label in (("new_font_revised.rsb", "pc_nfr"),
                      ("pda-lcd-02.rsb", "pc_pda"),
                      ("Chinese0.rsb", "cn0_final"),
                      ("gb1600.rsb", "gb1600_final")):
        p = os.path.join(ART, nm)
        b, mode, w, h, pp, bpp, need, tail = parse(p)
        A("\n### %s mode=%d %dx%d p=%s bpp=%d tail=%d" %
          (nm, mode, w, h, pp, bpp, tail))
        raw = b[SURF:SURF + need]
        if bpp == 16:
            u = np.frombuffer(raw, "<u2").reshape(h, w)
            ink = (u & 0xFF).astype(np.uint8)
            Image.fromarray(ink, "L").save(os.path.join(OUT, label + ".png"))
            vals, cnts = np.unique(u, return_counts=True)
            top = sorted(zip(cnts, vals), reverse=True)[:5]
            A("   u16 top: %s" % ", ".join("0x%04x×%d" % (v, c) for c, v in top))
            A("   -> %s.png" % label)
        elif bpp == 32:
            a = np.frombuffer(raw, np.uint8).reshape(h, w, 4)
            for i, cn in enumerate("BGRA"):
                A("   ch %s: 唯一值=%d 均值=%.1f" %
                  (cn, len(np.unique(a[:, :, i])), float(a[:, :, i].mean())))
            sheet = np.concatenate([a[:, :, i] for i in range(4)], axis=1)
            Image.fromarray(sheet, "L").save(os.path.join(OUT, label + "_BGRA.png"))
            # 用 B 通道 (或 G) 当墨
            ch = int(np.argmax([float(a[:, :, i].std()) for i in range(4)]))
            Image.fromarray(a[:, :, ch], "L").save(os.path.join(OUT, label + "_ink.png"))
            A("   -> %s_BGRA.png / %s_ink.png (ch=%d)" % (label, label, ch))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_rsb_final.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
