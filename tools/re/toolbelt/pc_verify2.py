#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_verify2.py -- 落盘核对 STRINGS.RES 首组 4 条与 strings.txt 抽样 (round77 自查)"""
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")

L = []
A = L.append
res = open(os.path.join(PC, "Data", "Shell", "STRINGS.RES"), "rb").read()
A("== STRINGS.RES 首组 (GameType0) 逐字段 ==")
p = 0x12
A("count @0x12 = %d" % int.from_bytes(res[0x12:0x16], "little"))
p = 0x16
for k in range(4):
    n = int.from_bytes(res[p:p + 4], "little")
    s = res[p + 4:p + 4 + n]
    A("  [%d] @0x%04X len=%-3d %s" % (k, p, n, s.decode("gbk")))
    p += 4 + n + 2
A("组尾 @0x%04X = %s" % (p, res[p:p + 4].hex()))

txt = open(os.path.join(PC, "Data", "Shell", "strings.txt"), "rb").read().decode("gbk")
A("\n== strings.txt 抽样 ==")
for ln in txt.splitlines():
    for k in ("WPN_FRAG", "ITM_BINOCULARS", "WPN_M9SD", "run", "use_item"):
        if re.search(r'"%s"' % re.escape(k), ln):
            A("  %s" % ln.strip())

A("\n== Chinese.dat 开头 40 字 ==")
dat = open(os.path.join(PC, "Chinese.dat"), "rb").read()
A("  " + "".join(dat[i:i + 2].decode("gbk") for i in range(0, 80, 2)))

t = "\n".join(L)
with io.open(os.path.join(OUT, "pc_verify2.txt"), "w",
             encoding="utf-8", newline="\n") as f:
    f.write(t + "\n")
