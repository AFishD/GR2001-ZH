#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_ps2_img.py -- 列 PS2 GR.IMG 条目名/扩展名 并抽取样本, 与 PC 同名格式对照 (round77 任务 C)

GR.IMG 条目表布局 (来自 docs/han_v2/FONT_CAPACITY.md §一.9):
  条目表 @0x830, 48B/条; 字段 [6]/[7]/[8] = stored / real / off
  名字区 0x34CB0..0x46475
"""
import io
import json
import os
import struct
import sys
import collections

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PS2ISO = os.path.join(ROOT, "third_party", "orig", "ps2",
                      "Tom Clancy's Ghost Recon (USA).iso")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
SEC = 2048


def iso_map(path):
    with open(path, "rb") as f:
        f.seek(16 * SEC)
        pvd = f.read(SEC)
    root = pvd[156:156 + 34]
    lba = struct.unpack_from("<I", root, 2)[0]
    size = struct.unpack_from("<I", root, 10)[0]
    with open(path, "rb") as f:
        f.seek(lba * SEC)
        d = f.read(size)
    ents = {}
    off = 0
    while off < len(d):
        ln = d[off]
        if ln == 0:
            off = (off // SEC + 1) * SEC
            if off >= len(d):
                break
            continue
        rec = d[off:off + ln]
        ext = struct.unpack_from("<I", rec, 2)[0]
        l = struct.unpack_from("<I", rec, 10)[0]
        nm = rec[33:33 + rec[32]].decode("latin-1")
        if nm not in ("\x00", "\x01"):
            ents[nm] = (ext, l)
        off += ln
    return ents


def main():
    ents = iso_map(PS2ISO)
    print("ISO9660 条目:", {k: (v[0], v[1]) for k, v in ents.items()})
    img = "GR.IMG;1"
    if img not in ents:
        print("no GR.IMG")
        return
    lba, length = ents[img]
    with open(PS2ISO, "rb") as f:
        f.seek(lba * SEC)
        head = f.read(0x50000)

    L = []
    A = L.append
    A("== GR.IMG @LBA %d size=%d (0x%x) ==" % (lba, length, length))
    A("条目表 @0x830:")
    ents_list = []
    i = 0
    while True:
        o = 0x830 + 48 * i
        if o + 48 > len(head):
            break
        f6, f7, f8 = struct.unpack_from("<III", head, o + 24)
        f0 = struct.unpack_from("<I", head, o)[0]
        ents_list.append((o, f0, f6, f7, f8))
        i += 1
        if i > 6000:
            break
    A("  扫到 %d 条 (停下时 off=0x%x)" % (len(ents_list), 0x830 + 48 * len(ents_list)))
    for o, f0, f6, f7, f8 in ents_list[:8]:
        A("    @0x%05x  f0=%-10d stored=%-10d real=%-10d off=0x%08x" % (o, f0, f6, f7, f8))

    # 名字区
    namearea = head[0x34CB0:0x46475]
    runs = []
    i2 = 0
    while i2 < len(namearea):
        j = namearea.find(b"\x00", i2)
        if j < 0 or j == i2:
            i2 = j + 1 if j >= 0 else len(namearea)
            continue
        s = namearea[i2:j]
        if all(32 <= c < 127 for c in s):
            runs.append((0x34CB0 + i2, s.decode("latin-1")))
        i2 = j + 1
    A("\n名字区串数 = %d (前 40)" % len(runs))
    for off, s in runs[:40]:
        A("  @0x%05x %r" % (off, s))

    exts = collections.Counter()
    for off, s in runs:
        e = os.path.splitext(s)[1].lower()
        exts[e] += 1
    A("\n== PS2 GR.IMG 名字区扩展名统计 ==")
    for k, v in exts.most_common():
        A("  %-8s %d" % (k or "(none)", v))

    t = "\n".join(L)
    with io.open(os.path.join(OUT, "ps2_gr_img_entries.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written")


if __name__ == "__main__":
    main()
