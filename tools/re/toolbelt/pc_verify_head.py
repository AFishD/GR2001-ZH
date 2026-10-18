#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_verify_head.py -- 核对 Chinese.dat / STRINGS.RES 开头串与几个关键词 (round77 自查)"""
import io
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")

L = []
A = L.append

dat = open(os.path.join(PC, "Chinese.dat"), "rb").read()
A("Chinese.dat 前 60 字: %s" % dat[:120].decode("gbk"))
A("Chinese.dat 前 20 个码: %s" % " ".join(dat[i:i+2].hex() for i in range(0, 40, 2)))
chars = "".join(dat[i:i+2].decode("gbk") for i in range(0, len(dat), 2))
for kw in ["失败", "恢复地", "出错", "名字", "人物", "胜利", "火并", "敌人"]:
    A("  Chinese.dat 含 %-6s = %s" % (kw, kw in chars))
A("Chinese.dat 唯一字 = %d, 全部 = %s" % (len(set(chars)), chars[:80]))

res = open(os.path.join(PC, "Data", "Shell", "STRINGS.RES"), "rb").read()
A("\nSTRINGS.RES @0x1A (6B) = %r" % res[0x1A:0x20].decode("gbk"))
A("STRINGS.RES @0x26 (4B) = %r" % res[0x26:0x2A].decode("gbk"))
A("STRINGS.RES @0x30 (26B) = %r" % res[0x30:0x4A].decode("gbk"))
A("'\\xca\\xa4\\xc0\\xfb\\xa3\\xa1' = %r" % b"\xca\xa4\xc0\xfb\xa3\xa1".decode("gbk"))
A("'\\xca\\xa7\\xb0\\xdc\\xa3\\xa1' = %r" % b"\xca\xa7\xb0\xdc\xa3\xa1".decode("gbk"))

txt = open(os.path.join(PC, "Data", "Shell", "strings.txt"), "rb").read().decode("gbk")
A("\nstrings.txt 前 3 个值: %s" % [l for l in txt.splitlines()[1:4]])

t = "\n".join(L)
with io.open(os.path.join(OUT, "pc_verify_head.txt"), "w",
             encoding="utf-8", newline="\n") as f:
    f.write(t + "\n")
print(t.encode("utf-8", "replace").decode("ascii", "replace"))
