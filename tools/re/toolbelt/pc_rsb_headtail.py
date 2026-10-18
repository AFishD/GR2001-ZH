#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_headtail.py -- dump .rsb 头部/尾部字节, 定性 mode 相关的附属块 (round77)"""
import io
import os
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ART = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "Data", "Shell", "Art")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def hx(b):
    return " ".join("%02x" % c for c in b)


def main():
    L = []
    A = L.append
    cases = [("Chinese0.rsb", 6, 28), ("gb1600.rsb", 9, 32),
             ("gb1200.rsb", 9, 32), ("new_font_revised.rsb", 9, 32),
             ("hud.rsb", 5, 28), ("reticle_pistol.rsb", 4, 28),
             ("cmi.rsb", 6, 28), ("main_menu-01.rsb", 6, 28)]
    for nm, mode, core in cases:
        b = open(os.path.join(ART, nm), "rb").read()
        A("### %-24s mode=%d size=%d" % (nm, mode, len(b)))
        A("    0x00..0x%02x (core): %s" % (core, hx(b[:core])))
        A("    core..0x40         : %s" % hx(b[core:0x40]))
        A("    末 80 字节          : %s" % hx(b[-80:]))
        A("")
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_rsb_headtail.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
