#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_charset_rel.py -- Chinese.dat / gbtext.def / strings.txt / STRINGS.RES 关系 (round77 任务 B)

回答: Chinese.dat 是什么类别, 与磅表/字形页的关系。
"""
import collections
import io
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def main():
    dat = open(os.path.join(PC, "Chinese.dat"), "rb").read()
    gbd = open(os.path.join(PC, "Data", "Shell", "Art", "gbtext.def"),
               "rb").read()
    L = []
    A = L.append

    dset = [dat[i:i + 2] for i in range(0, len(dat), 2)]
    gset = [gbd[i:i + 2] for i in range(0, len(gbd), 2)]
    A("== 集合 ==")
    A("  Chinese.dat      %d 码 (%d 唯一)" % (len(dset), len(set(dset))))
    A("  gbtext.def       %d 码 (%d 唯一)" % (len(gset), len(set(gset))))
    A("  Chinese.dat ⊆ gbtext.def = %s  (差 %d 个)" %
      (set(dset) <= set(gset), len(set(dset) - set(gset))))
    A("  gbtext.def ⊆ Chinese.dat = %s  (差 %d 个)" %
      (set(gset) <= set(dset), len(set(gset) - set(dset))))
    only_d = sorted(set(dset) - set(gset))
    only_g = sorted(set(gset) - set(dset))
    try:
        A("  只在 Chinese.dat 的 %d 个: %s" %
          (len(only_d), "".join(c.decode("gbk") for c in only_d)))
        A("  只在 gbtext.def  的 %d 个: %s" %
          (len(only_g), "".join(c.decode("gbk") for c in only_g[:200])))
    except UnicodeDecodeError as e:
        A("  解码异常 %s" % e)

    # strings.txt / STRINGS.RES 用字
    txt = open(os.path.join(PC, "Data", "Shell", "strings.txt"), "rb").read()
    s = txt.decode("gbk", "replace")
    sset = set()
    for ch in s:
        if ord(ch) >= 0x80:
            sset.add(ch.encode("gbk"))
    A("\n  strings.txt 非 ASCII 字 %d 个" % len(sset))
    A("  strings.txt 用字 ⊆ gbtext.def = %s (差 %d)" %
      (sset <= set(gset), len(sset - set(gset))))
    A("  strings.txt 用字 ⊆ Chinese.dat = %s (差 %d)" %
      (sset <= set(dset), len(sset - set(dset))))

    # STRINGS.RES 全量
    res = open(os.path.join(PC, "Data", "Shell", "STRINGS.RES"), "rb").read()
    try:
        rtxt = res.decode("gbk", "replace")
    except Exception:
        rtxt = ""
    rset = set()
    for ch in rtxt:
        if ord(ch) >= 0x80:
            try:
                rset.add(ch.encode("gbk"))
            except Exception:
                pass
    A("  STRINGS.RES 非 ASCII 字(粗) %d" % len(rset))
    A("  STRINGS.RES 用字 ⊆ gbtext.def = %s (差 %d)" %
      (rset <= set(gset), len(rset - set(gset))))

    # 全语料 (strings.txt + STRINGS.RES + Chinese.dat + gbtext.def)
    A("\n== 全字形页覆盖面 ==")
    A("  gbtext.def 1288 字 = 引擎实际会查的码位 (map: code->slot 0..1287)")
    A("  12px: perRow=512/12=42 perPage=42*42=1764 -> 1 页 (GB1200.TGA) 1764 槽 >= 1288 ✓")
    A("  16px: perRow=32      perPage=1024      -> 2 页 (GB1600/1601)    2048 槽 >= 1288 ✓")
    A("  24px: perRow=21      perPage=441       -> 3 页 (GB2400/01/02)   1323 槽 >= 1288 ✓")
    A("  页数上限 = 每字号 5 页 (0x6584c3 `cmp ebp,5`)")
    A("  字号扫描范围 = 1..39 (0x6584d1 `cmp edi,0x28`)")
    A("  slot 宽度 = u16 (0x6582dd `mov word [edx+0xE], si`)")
    A("  ⇒ 12px 理论容量 5*1764 = 8820 槽 (>= GB2312 全体 7445)")

    # Chinese.dat 字符全集落盘
    with io.open(os.path.join(OUT, "Chinese_dat_chars.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write("".join(c.decode("gbk", "replace") for c in dset) + "\n")
    with io.open(os.path.join(OUT, "gbtext_def_chars.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write("".join(c.decode("gbk", "replace") for c in gset) + "\n")

    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_charset_rel.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t.encode("utf-8", "replace").decode("ascii", "replace"))


if __name__ == "__main__":
    main()
