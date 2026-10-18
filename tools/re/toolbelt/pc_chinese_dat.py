#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_chinese_dat.py -- 解码 PC 版 Chinese.dat (GBK 串表) + 中文资源普查 (任务 B)

产物:
  work/builds/GR_ZH98/temp/r77/Chinese_dat.txt   一行一条, 带偏移
  work/builds/GR_ZH98/temp/r77/Chinese_dat_report.txt
"""
import io
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)

SRC = os.path.join(PC, "Chinese.dat")


def main():
    b = open(SRC, "rb").read()
    L = []
    A = L.append
    A("file   = %s" % SRC)
    A("size   = %d bytes" % len(b))

    # 1) 结构探针: 头部 + 分隔符统计
    A("\n-- head 64 --")
    A(" ".join("%02x" % c for c in b[:64]))
    seps = {}
    for c in b:
        if c < 0x20:
            seps[c] = seps.get(c, 0) + 1
    A("control-byte histogram: " +
      ", ".join("0x%02x=%d" % (k, v) for k, v in sorted(seps.items())))

    # 2) 判断是否有 \r\n / \0 分隔
    for sep in (b"\x00", b"\r\n", b"\n", b"\r"):
        A("count %-6r = %d" % (sep, b.count(sep)))

    # 3) 逐条切分: 先试 \x00 分隔, 再试换行
    def emit(records, how):
        A("\n===== split by %s : %d records =====" % (how, len(records)))
        for off, raw in records:
            try:
                s = raw.decode("gbk")
            except UnicodeDecodeError as e:
                s = raw.decode("gbk", "replace") + "   <GBK-ERR %s>" % e
            A("  @0x%04x len=%-4d %r" % (off, len(raw), s))

    nul = []
    off = 0
    for part in b.split(b"\x00"):
        if part:
            nul.append((off, part))
        off += len(part) + 1
    emit(nul, "\\x00")

    # 4) 全文按 \x00 -> 换行 的解码视图
    lines = []
    for off, raw in nul:
        try:
            s = raw.decode("gbk")
        except UnicodeDecodeError:
            s = raw.decode("gbk", "replace")
        lines.append((off, len(raw), s))

    # 5) 落盘: 一行一条, 带偏移
    with io.open(os.path.join(OUT, "Chinese_dat.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write("# PC Ghost Recon Chinese.dat 解码 (GBK), 生成者 tools/re/toolbelt/pc_chinese_dat.py\n")
        f.write("# 源: third_party/orig/ghost_recon_pc/Chinese.dat  size=%d\n" % len(b))
        f.write("# 格式: <hex偏移>\t<字节长>\t<GBK解码文本>\n")
        for off, ln, s in lines:
            f.write("0x%04X\t%d\t%s\n" % (off, ln, s))

    # 6) 分类统计
    import collections
    kinds = collections.Counter()
    for off, ln, s in lines:
        if any("\u4e00" <= ch <= "\u9fff" for ch in s):
            kinds["has-CJK"] += 1
        elif s.strip() == "":
            kinds["blank"] += 1
        else:
            kinds["ascii/punct"] += 1
    A("\n-- classify --")
    for k, v in kinds.most_common():
        A("  %-14s %d" % (k, v))

    t = "\n".join(L)
    with io.open(os.path.join(OUT, "Chinese_dat_report.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
