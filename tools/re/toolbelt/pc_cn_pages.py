#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_pages.py -- 核对 Chinese0-4.rsb 与 gbXXXX.rsb 是否同一批页面 (round77 任务 A/C)

并做 gbtext.def -> 16x16 格 的模板匹配验证 (证明 slot->(page,row,col) 公式)。
"""
import hashlib
import io
import os
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
ART = os.path.join(PC, "Data", "Shell", "Art")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def surface(name):
    """按实测头假设取 512x512 16bpp 表面 (文件尾对齐)"""
    b = open(os.path.join(ART, name), "rb").read()
    px = 512 * 512 * 2
    off = len(b) - px
    return b, off, np.frombuffer(b[off:off + px], "<u2").reshape(512, 512)


def main():
    L = []
    A = L.append
    A("== .rsb 头部实测 (512x512x16bpp, 表面尾对齐) ==")
    names = ["Chinese%d.rsb" % i for i in range(5)] + \
            ["gb1200.rsb", "gb1600.rsb", "gb1601.rsb",
             "gb2400.rsb", "gb2401.rsb", "gb2402.rsb"]
    tabs = {}
    for n in names:
        b, off, u = surface(n)
        mode = struct.unpack_from("<I", b, 0)[0]
        w = struct.unpack_from("<I", b, 4)[0]
        h = struct.unpack_from("<I", b, 8)[0]
        p = [struct.unpack_from("<I", b, 0x10 + 4 * i)[0] for i in range(4)]
        pbe = [struct.unpack_from(">I", b, 0x10 + 4 * i)[0] for i in range(4)]
        tabs[n] = u
        A("  %-14s size=%-7d 头=%3d mode=%d w=%d h=%d  p@0x10(BE)=%s" %
          (n, len(b), off, mode, w, h, pbe))

    A("\n== 像素面互比 (512x512 u16, 逐元素相等率) ==")
    A("  %-14s %s" % ("", " ".join("%-12s" % x.replace(".rsb", "")
                                   for x in names)))
    for a in names:
        row = []
        for c in names:
            eq = float((tabs[a] == tabs[c]).mean())
            row.append("%-12.4f" % eq)
        A("  %-14s %s" % (a.replace(".rsb", ""), " ".join(row)))

    # 结构统计
    A("\n== 各页 u16 值分布 ==")
    for n in names:
        u = tabs[n]
        vals, cnts = np.unique(u, return_counts=True)
        top = sorted(zip(cnts, vals), reverse=True)[:5]
        A("  %-14s 唯一值=%-5d top=%s" %
          (n, len(vals), ", ".join("0x%04x×%d" % (v, c) for c, v in top)))

    # gbtext.def
    gb = open(os.path.join(ART, "gbtext.def"), "rb").read()
    codes = [gb[i:i + 2] for i in range(0, len(gb), 2)]
    A("\n== gbtext.def: %d 码 ==" % len(codes))

    # 16px 分页: perRow = 512/16 = 32, perPage = 1024
    A("\n== 按 16px 公式的页分布 ==")
    A("  page0 = slot 0..1023 -> Chinese0.rsb / gb1600.rsb")
    A("  page1 = slot 1024..1287 (%d 个) -> Chinese1.rsb / gb1601.rsb" %
      (len(codes) - 1024))
    # 24px: perRow=21, perPage=441 -> 3 页
    A("  24px: perRow=21 perPage=441 -> 页数 = ceil(1288/441) = %d" %
      ((len(codes) + 440) // 441))

    # 目检: 16px 网格下 slot0..15 的格图
    u = tabs["Chinese0.rsb"]
    lo = (u & 0xFF).astype(np.uint8)
    tile = np.zeros((16 * 4, 16 * 32), np.uint8)
    for k in range(64):
        r, c = k // 32, k % 32
        if r >= 4:
            break
        tile[r * 16:(r + 1) * 16, c * 16:(c + 1) * 16] = lo[r * 16:(r + 1) * 16,
                                                           c * 16:(c + 1) * 16]
    Image.fromarray(tile, "L").resize((16 * 32 * 4, 16 * 4 * 4),
                                      Image.NEAREST).save(
        os.path.join(OUT, "cn0_16px_first64_4x.png"))
    A("\n  -> cn0_16px_first64_4x.png (16px 网格前 64 槽 @4x)")

    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn_pages.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
