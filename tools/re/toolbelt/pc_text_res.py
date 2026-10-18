#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_text_res.py -- PC 版文本资源剖析 (round77 任务 B)

对象:
  Data/Shell/strings.txt   源串表 (GBK)
  Data/Shell/STRINGS.RES   编译后串表
  Chinese.dat              疑似字符集表
  Data/Shell/IKE.RES       通用资源
产物 -> work/builds/GR_ZH98/temp/r77/
"""
import io
import os
import re
import struct
import sys
import collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)


def rd(p):
    with open(p, "rb") as f:
        return f.read()


def dump(b, off=0, n=256):
    out = []
    for i in range(off, min(off + n, len(b)), 16):
        c = b[i:i + 16]
        out.append("%08x  %-47s  %s" % (i, " ".join("%02x" % x for x in c),
                                        "".join(chr(x) if 32 <= x < 127 else "." for x in c)))
    return "\n".join(out)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def w(s):
    with io.open(s[0], "w", encoding="utf-8", newline="\n") as f:
        f.write(s[1] + "\n")


# ---------------------------------------------------------------- Chinese.dat

def do_chinese_dat():
    b = rd(os.path.join(PC, "Chinese.dat"))
    L = []
    A = L.append
    A("== Chinese.dat  size=%d ==" % len(b))
    A("len %% 2 = %d  -> %d 个双字节槽位" % (len(b) % 2, len(b) // 2))
    chars = []
    bad = []
    for i in range(0, len(b) - 1, 2):
        pair = b[i:i + 2]
        try:
            s = pair.decode("gbk")
        except UnicodeDecodeError:
            bad.append((i, pair))
            s = "\ufffd"
        chars.append((i, pair, s))
    A("GBK 解码失败槽位 = %d" % len(bad))
    for off, pair in bad:
        A("   @0x%04x %s" % (off, pair.hex()))

    # 去重统计
    txt = "".join(c[2] for c in chars)
    A("总槽位 = %d, 去重字符 = %d, 重复 = %d" %
      (len(chars), len(set(txt)), len(chars) - len(set(txt))))
    A("ASCII/半角槽位 = %d" % sum(1 for c in chars if ord(c[2]) < 0x80))
    A("CJK 统一表意槽位 = %d" % sum(1 for c in chars if "\u4e00" <= c[2] <= "\u9fff"))
    A("其它(CJK标点/全角/希腊等) = %d" %
      sum(1 for c in chars if ord(c[2]) >= 0x80 and not ("\u4e00" <= c[2] <= "\u9fff")))

    # 域分布: GB2312 区位
    zones = collections.Counter()
    for off, pair, s in chars:
        if len(pair) == 2 and pair[0] >= 0xA1:
            zones[pair[0]] += 1
    A("\n-- GBK lead byte 分布 (top 40) --")
    for k, v in zones.most_common(40):
        A("  0x%02X : %d" % (k, v))

    # 是否排序?
    sorted_pairs = sorted(b[i:i + 2] for i in range(0, len(b) - 1, 2))
    A("\n按字节序是否已排序 = %s" % (sorted_pairs == [b[i:i + 2] for i in range(0, len(b) - 1, 2)]))

    # 输出全部 1101 条
    A("\n-- 全部槽位 --")
    for i, (off, pair, s) in enumerate(chars):
        A("  [%4d] @0x%04X  %s  %s" % (i, off, pair.hex(), s))

    # 落盘: 一行一条带偏移
    lines = ["# PC Ghost Recon Chinese.dat 解码 (GBK, 双字节槽位)",
             "# 源: third_party/orig/ghost_recon_pc/Chinese.dat  size=%d" % len(b),
             "# 结构: 无分隔符, 纯双字节 GBK 序列 (len/2 槽位), 无 NUL/换行",
             "# 格式: <hex偏移>\\t<索引>\\t<GBK字节>\\t<字符>"]
    for i, (off, pair, s) in enumerate(chars):
        lines.append("0x%04X\t%d\t%s\t%s" % (off, i, pair.hex(), s))
    w((os.path.join(OUT, "Chinese_dat.txt"), "\n".join(lines)))
    w((os.path.join(OUT, "Chinese_dat_report.txt"), "\n".join(L)))

    # 纯文本版(一行 = 全部字符, 另存便于阅读)
    w((os.path.join(OUT, "Chinese_dat_chars.txt"),
       "".join(c[2] for c in chars)))
    return "\n".join(L)


# ---------------------------------------------------------------- strings.txt

def do_strings_txt():
    p = os.path.join(PC, "Data", "Shell", "strings.txt")
    b = rd(p)
    L = []
    A = L.append
    A("== strings.txt size=%d ==" % len(b))
    try:
        t = b.decode("gbk")
        enc = "gbk"
    except UnicodeDecodeError:
        t = b.decode("utf-8", "replace")
        enc = "utf-8(replace)"
    A("解码 = %s" % enc)
    lines = t.splitlines()
    A("行数 = %d" % len(lines))
    kvs = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("//"):
            continue
        mm = re.findall(r'"([^"]*)"', s)
        if len(mm) >= 2:
            kvs.append((i + 1, mm[0], mm[1]))
    A("键值对 = %d" % len(kvs))
    A("唯一键 = %d" % len(set(k for _, k, _ in kvs)))
    A("值含中文 = %d" % sum(1 for _, _, v in kvs if any("\u4e00" <= c <= "\u9fff" for c in v)))
    # 最长值
    tops = sorted(kvs, key=lambda x: -len(x[2]))
    A("\n-- 最长的 20 条值(长度证据) --")
    for ln, k, v in tops[:20]:
        A("  L%-5d k=%-24s len=%-4d %r" % (ln, k, len(v), v))
    A("\n-- 全部键值对 --")
    for ln, k, v in kvs:
        A("  L%-5d %-30s = %s" % (ln, k, v))
    txt = "\n".join(L)
    w((os.path.join(OUT, "pc_strings_txt.txt"), txt))
    return "\n".join(L[:40]) + "\n...(全量见 pc_strings_txt.txt)"


# ---------------------------------------------------------------- STRINGS.RES

def do_strings_res():
    p = os.path.join(PC, "Data", "Shell", "STRINGS.RES")
    b = rd(p)
    L = []
    A = L.append
    A("== STRINGS.RES size=%d ==" % len(b))
    A(dump(b, 0, 192))

    # 头部猜测
    A("\n-- u32 头 16 个 --")
    for i in range(0, 64, 4):
        A("  +0x%02x = %-12d 0x%08x" % (i, u32(b, i), u32(b, i)))

    # 找 UTF-16LE 串
    A("\n-- UTF-16LE 串探针 (>=4 字符) --")
    n16 = 0
    i = 0
    samples = []
    while i < len(b) - 4:
        if 32 <= b[i] < 0x200 and b[i + 1] == 0:
            j = i
            while j < len(b) - 1 and b[j + 1] == 0 and b[j] >= 0x20:
                j += 2
            if j - i >= 8:
                n16 += 1
                if len(samples) < 10:
                    samples.append((i, b[i:j].decode("utf-16-le", "replace")))
            i = j
        else:
            i += 1
    A("  UTF-16LE 串数量 = %d" % n16)
    for off, s in samples:
        A("    @0x%06x %r" % (off, s))

    # 找 GBK/ASCII 串
    A("\n-- ASCII/GBK 串探针 (>=5) --")
    i = 0
    n = 0
    samples = []
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and (32 <= b[j] < 127 or b[j] >= 0x81):
                j += 1
            if j - i >= 5:
                n += 1
                if len(samples) < 20:
                    try:
                        s = b[i:j].decode("gbk")
                    except UnicodeDecodeError:
                        s = b[i:j].decode("latin-1")
                    samples.append((i, s))
            i = j
        else:
            i += 1
    A("  串数量 = %d" % n)
    for off, s in samples:
        A("    @0x%06x %r" % (off, s))

    txt = "\n".join(L)
    w((os.path.join(OUT, "pc_strings_res_probe.txt"), txt))

    # ---- 正式解析 ----
    P = []
    B = P.append
    B("== STRINGS.RES 解析 ==")
    n0 = u32(b, 0)
    B("头 u32 = %d" % n0)
    p = 4
    groups = []
    while p + 4 <= len(b):
        nl = u32(b, p)
        if nl == 0 or nl > 128:
            break
        name = b[p + 4:p + 4 + nl]
        if not all(32 <= c < 127 for c in name):
            break
        name = name.decode("latin-1")
        q = p + 4 + nl
        if b[q] != 0:
            break
        q += 1
        cnt = u32(b, q)
        q += 4
        items = []
        ok = True
        for _ in range(cnt):
            if q + 4 > len(b):
                ok = False
                break
            sl = u32(b, q)
            q += 4
            if sl == 0 or sl > 65535 or q + sl + 2 > len(b):
                ok = False
                break
            raw = b[q:q + sl]
            q += sl
            if b[q:q + 2] != b"\x00\x00":
                ok = False
                break
            q += 2
            try:
                items.append(raw.decode("gbk"))
            except UnicodeDecodeError:
                items.append(raw.decode("gbk", "replace"))
        if not ok or len(items) != cnt:
            B("!! 组 %r 解析中断于 0x%x (cnt=%d got=%d)" % (name, q, cnt, len(items)))
            break
        # 组尾 4 字节 0
        if b[q:q + 4] == b"\x00\x00\x00\x00":
            q += 4
        groups.append((p, name, items))
        p = q
    B("解析到 %d 组, 收尾偏移 0x%x / 文件 %d, 剩余 %d" %
      (len(groups), p, len(b), len(b) - p))
    B("总条目 = %d, 总字符 = %d" %
      (sum(len(g[2]) for g in groups),
       sum(len(s) for g in groups for s in g[2])))
    t2 = ["# STRINGS.RES 全量解析 (GBK)",
          "# 组数=%d 条目=%d" % (len(groups), sum(len(g[2]) for g in groups))]
    for off, name, items in groups:
        t2.append("\n### [0x%06X] %s  (%d)" % (off, name, len(items)))
        for k, s in enumerate(items):
            t2.append("  [%d] %s" % (k, s))
    w((os.path.join(OUT, "pc_STRINGS_RES_dump.txt"), "\n".join(t2)))
    B("\n-- 组名列表 --")
    for off, name, items in groups:
        B("  @0x%06X %-28s n=%d" % (off, name, len(items)))
    txt = "\n".join(P)
    w((os.path.join(OUT, "pc_strings_res_parse.txt"), txt))
    return txt


# ---------------------------------------------------------------- main

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "dat":
        print(do_chinese_dat())
    elif cmd == "txt":
        print(do_strings_txt())
    elif cmd == "res":
        print(do_strings_res())
    else:
        do_chinese_dat()
        do_strings_txt()
        do_strings_res()
        print("done ->", OUT)


if __name__ == "__main__":
    main()
