#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_sxm.py -- 抽 GhostRecon.exe 的 SXM/SXME RCDATA 资源, 复原拉丁字形度量记录 (round77 任务 A3)

对照 PS2 FONT.RES 记录 {u8 f0}{u8 f1=advance}{u16 u0}{u16 v0}{u16 u1}{u16 v1}
"""
import io
import os
import struct

import pefile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXE = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "GhostRecon.exe")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def main():
    pe = pefile.PE(EXE)
    blob = open(EXE, "rb").read()
    L = []
    A = L.append
    A("== RT_RCDATA 资源里 type 名含 SXM 的 ==")
    got = {}
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        A("  无资源目录")
    else:
        for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
            tn = t.name
            if tn is None:
                tn = pefile.RESOURCE_TYPE.get(t.struct.Id, str(t.struct.Id))
            if "SXM" not in str(tn):
                continue
            for rid in t.directory.entries:
                for lang in rid.directory.entries:
                    d = lang.data.struct
                    raw = blob[d.OffsetToData:d.OffsetToData + d.Size]
                    nm = rid.name if rid.name else rid.struct.Id
                    got[str(nm)] = raw
                    A("  type=%-6s id=%-14s size=%d" % (tn, nm, len(raw)))
    A("\n  共 %d 个 SXM* 资源" % len(got))

    for nm, raw in sorted(got.items()):
        A("\n### %s  size=%d" % (nm, len(raw)))
        A("  head: %s" % raw[:64].hex())
        # 若可作为 10 字节/字形 解析
        for stride in (10, 8):
            n = len(raw) // stride
            if n * stride != len(raw):
                continue
            A("  -- 按 %d 字节/条: 共 %d 条 --" % (stride, n))
            rows = []
            for k in range(min(12, n)):
                seg = raw[k * stride:(k + 1) * stride]
                vals = struct.unpack("<" + "B" * stride, seg)
                rows.append(vals)
            for k, v in enumerate(rows):
                A("    [%3d] %s" % (k, v))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_sxm.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written", len(t))
    print(t[:2000].encode("utf-8", "replace").decode("ascii", "replace"))


if __name__ == "__main__":
    main()
