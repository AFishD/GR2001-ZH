#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_exe_strings.py -- 在 PC 版 EXE/DLL 里搜字体与中文相关字符串 (round77)

证明: PC 引擎如何找字体/中文资源 (任务 A1/A2/B3/D1)
"""
import io
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)

TARGETS = ["GhostRecon.exe", "igor.exe", "ScriptEd.dll",
           os.path.join("ubicom", "ubicom.dll")]

PATS = [b"Chinese", b"chinese", b"CHINESE", b"Chinese%d", b".dat",
        b"font.res", b"font", b"Font", b"FONT", b"gbtext", b".rsb", b"RSB",
        b"STRINGS.RES", b"strings.res", b"strings.txt", b"new_font_revised",
        b"pda_counterparts", b"COMMON.PAK", b"common.pak",
        b"ASCII", b"DBCS", b"Big5", b"GB2312", b"cp936", b"936"]


def ascii_runs(b, minlen=4):
    return [(m.start(), m.group().decode("latin-1"))
            for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minlen, b)]


def main():
    L = []
    A = L.append
    for t in TARGETS:
        p = os.path.join(PC, t)
        if not os.path.exists(p):
            A("MISSING %s" % t)
            continue
        b = open(p, "rb").read()
        A("=" * 78)
        A("### %s  size=%d (0x%x)" % (t, len(b), len(b)))
        for pat in PATS:
            idxs = [m.start() for m in re.finditer(re.escape(pat), b)]
            if not idxs:
                continue
            A("  %-20r count=%-5d first=%s" %
              (pat, len(idxs), " ".join("0x%x" % i for i in idxs[:10])))
        A("  -- ascii runs containing font/chinese/rsb --")
        for off, s in ascii_runs(b, 4):
            low = s.lower()
            if any(k in low for k in ("font", "chinese", "rsb", "gbtext",
                                      ".res", "strings", "pda_count",
                                      "\u5b57")):
                A("    @0x%07x %r" % (off, s))
        # UTF-16LE 版
        A("  -- utf16le runs containing font/chinese --")
        i = 0
        n = 0
        while i < len(b) - 8:
            if 32 <= b[i] < 127 and b[i + 1] == 0:
                j = i
                while j < len(b) - 1 and b[j + 1] == 0 and 32 <= b[j] < 127:
                    j += 2
                if j - i >= 8:
                    s = b[i:j].decode("utf-16-le", "replace")
                    low = s.lower()
                    if any(k in low for k in ("font", "chinese", "rsb",
                                              "gbtext", ".res", "strings")):
                        A("    @0x%07x %r" % (i, s))
                        n += 1
                i = j
            else:
                i += 1
        A("  (utf16 hits=%d)" % n)
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_exe_strings.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written", len(t), "bytes")


if __name__ == "__main__":
    main()
