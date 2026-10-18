#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_homology.py -- PC vs PS2 格式同源性对照 (round77 任务 C)

对照对象: .mis / .atr / .gun / .kit / .qob / .pob / .rsb
PS2 侧素材: docs/han_v2/mis_decoded/*.MIS (已解码), docs/han_v2/artifacts/*,
            tools/text_csv/tcslib.py 的容器读取
"""
import io
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
HAN = os.path.join(ROOT, "docs", "han_v2")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)


def dump(b, off=0, n=128):
    out = []
    for i in range(off, min(off + n, len(b)), 16):
        c = b[i:i + 16]
        out.append("%08x  %-47s  %s" % (i, " ".join("%02x" % x for x in c),
                                        "".join(chr(x) if 32 <= x < 127 else "." for x in c)))
    return "\n".join(out)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def ascii_runs(b, minlen=4, lim=40):
    res = []
    i = 0
    while i < len(b) and len(res) < lim:
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and 32 <= b[j] < 127:
                j += 1
            if j - i >= minlen:
                res.append((i, b[i:j].decode("latin-1")))
            i = j
        else:
            i += 1
    return res


def main():
    L = []
    A = L.append

    # ---------- 1) MIS ----------
    A("=" * 90)
    A("### 1) .MIS  PC vs PS2(解码后)")
    pairs = [
        ("M01_CAVES", "m01_caves.mis"),
        ("M02_FARM", "m02_farm.mis"),
        ("M15_RED_SQUARE", "m15_red_square.mis"),
        ("T01", "t01.mis"),
        ("TRAINING_MP", "training_mp.mis"),
    ]
    for ps2n, pcn in pairs:
        p2 = os.path.join(HAN, "mis_decoded", ps2n + ".MIS")
        p1 = os.path.join(PC, "Mods", "Origmiss", "Mission", pcn)
        if not (os.path.exists(p1) and os.path.exists(p2)):
            A("  MISSING %s / %s" % (p2, p1))
            continue
        b1 = open(p1, "rb").read()
        b2 = open(p2, "rb").read()
        A("\n-- %s --" % ps2n)
        A("  PC   %-24s size=%-8d head=%s" % (pcn, len(b1), b1[:16].hex()))
        A("  PS2d %-24s size=%-8d head=%s" % (ps2n + ".MIS", len(b2), b2[:16].hex()))
        A("  共同前缀字节数 = %d" % next((i for i in range(min(len(b1), len(b2)))
                                          if b1[i] != b2[i]), min(len(b1), len(b2))))
        A("  PC   u32[0..7] = %s" % [u32(b1, 4 * i) for i in range(8)])
        A("  PS2d u32[0..7] = %s" % [u32(b2, 4 * i) for i in range(8)])
        A("  PC   ascii: %s" % ascii_runs(b1, 5, 8))
        A("  PS2d ascii: %s" % ascii_runs(b2, 5, 8))
        A("  PC head dump:")
        A(dump(b1, 0, 64))
        A("  PS2d head dump:")
        A(dump(b2, 0, 64))

    # ---------- 2) 扩展名清单 ----------
    A("\n" + "=" * 90)
    A("### 2) PC 侧 .atr/.gun/.kit/.qob/.pob 抽样头部")
    for ext in (".atr", ".gun", ".kit", ".qob", ".pob", ".map", ".gtf", ".rsb"):
        found = []
        for dp, dn, fn in os.walk(PC):
            for f in fn:
                if f.lower().endswith(ext):
                    found.append(os.path.join(dp, f))
        found.sort(key=lambda p: os.path.getsize(p))
        A("\n-- %s : %d 个 --" % (ext, len(found)))
        for p in (found[:2] + found[len(found) // 2:len(found) // 2 + 2] + found[-2:]):
            b = open(p, "rb").read()
            A("  %-72s size=%-9d head=%s" %
              (os.path.relpath(p, PC), len(b), b[:24].hex()))
            A("      u32[0..5]=%s  ascii=%s" %
              ([u32(b, 4 * i) for i in range(6)], ascii_runs(b, 4, 4)))

    # ---------- 3) PC 的 VFS/搜索路径 ----------
    A("\n" + "=" * 90)
    A("### 3) PC 版资源搜索路径 (来自 exe 字面量 0x8c10f0 附近)")
    exe = open(os.path.join(PC, "GhostRecon.exe"), "rb").read()
    i = exe.find(b"\\data\\shell\\fonts")
    if i > 0:
        seg = exe[i - 8:i + 400]
        A("  file=0x%x" % i)
        for s in ascii_runs(seg, 3, 60):
            A("    +0x%03x %r" % (s[0] - 8, s[1]))

    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_homology.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written", len(t))


if __name__ == "__main__":
    main()
