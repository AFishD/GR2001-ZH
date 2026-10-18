#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_probe.py -- PC .rsb 头部结构探针 (round77 任务 A/C)

判定 PC .rsb 是「wire rsb」{mode,w,h,p0..p3}+CLUT+surface 还是别的。
只读。输出 -> work/builds/GR_ZH98/temp/r77/
"""
import io
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)

FILES = [
    "Data/Shell/Art/new_font_revised.rsb",
    "Data/Shell/Art/Chinese0.rsb",
    "Data/Shell/Art/Chinese1.rsb",
    "Data/Shell/Art/Chinese2.rsb",
    "Data/Shell/Art/Chinese3.rsb",
    "Data/Shell/Art/Chinese4.rsb",
    "Data/Shell/Art/pda-lcd-02.rsb",
    "Data/Shell/Art/cmi.rsb",
    "Data/Shell/Art/hud.rsb",
    "Data/Shell/Art/reticle_pistol.rsb",
    "Data/Shell/Art/main_menu-01.rsb",
    "Data/Shell/Art/load_icon.rsb",
    "Data/Shell/Art/gb1200.rsb",
]

PIXFMT = {0: "?", 1: "?", 2: "?", 3: "?", 4: "?", 5: "?"}


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def rd(p):
    with open(p, "rb") as f:
        return f.read()


def dump(b, off, n, base=0):
    out = []
    for i in range(off, min(off + n, len(b)), 16):
        c = b[i:i + 16]
        out.append("%08x  %-47s  %s" % (base + i,
                                        " ".join("%02x" % x for x in c),
                                        "".join(chr(x) if 32 <= x < 127 else "." for x in c)))
    return "\n".join(out)


def main():
    L = []
    A = L.append
    for rel in FILES:
        p = os.path.join(PC, rel)
        if not os.path.exists(p):
            A("MISSING %s" % rel)
            continue
        b = rd(p)
        A("=" * 78)
        A("### %s   size=%d (0x%x)" % (rel, len(b), len(b)))
        A(dump(b, 0, 64))
        # 猜: 前 28B = {mode,w,h,p0,p1,p2,p3}
        mode, w, h, p0, p1, p2, p3 = struct.unpack_from("<7I", b, 0)
        A("  guessA {mode=%d w=%d h=%d p=(%d,%d,%d,%d)}  w*h=%d  w*h+28=%d  len-28=%d" %
          (mode, w, h, p0, p1, p2, p3, w * h, w * h + 28, len(b) - 28))
        # 猜: 尾对齐 -> 表面在文件尾
        for bpp, tag in ((1, "8bpp"), (0.5, "4bpp"), (2, "16bpp"), (4, "32bpp")):
            px = int(w * h * bpp)
            if 0 < px <= len(b):
                A("    tail-surface %s: %d bytes -> header+clut = %d" %
                  (tag, px, len(b) - px))
        # 找可打印名
        A("  head-ascii: %r" % b[:32])
        A("")
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_rsb_probe.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
