#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_load.py -- 找 PC 版中文页 (Chinese0-4.rsb) 的加载代码与页数硬编码 (round77 任务 A2/D1)"""
import io
import os
import re
import struct

import capstone
import pefile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")

EXE = os.path.join(PC, "GhostRecon.exe")


def main():
    pe = pefile.PE(EXE, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    b = open(EXE, "rb").read()
    L = []
    A = L.append

    def f2v(f):
        for s in pe.sections:
            p = s.PointerToRawData
            if p <= f < p + s.SizeOfRawData:
                return base + s.VirtualAddress + (f - p)
        return None

    A("== 搜 'Chinese' / 'gbtext' / 'GB2312' 相关字面量 ==")
    for pat in (b"Chinese", b"GB2312", b"gbtext", b"BIG5", b"Big5", b"\\fonts",
                b"font.res", b"new_font_revised", b"pda_counterparts",
                b"Chinese0", b"Chinese%d", b"chinese", b".def", b"CHINESE"):
        hits = [m.start() for m in re.finditer(re.escape(pat), b)]
        if not hits:
            continue
        A("\n  %-20r  %d 处" % (pat, len(hits)))
        for h in hits[:14]:
            # 取周围 64 字节的可打印串
            s = b[max(0, h - 48):h + 64]
            s = re.sub(rb"[^\x20-\x7e]", b".", s).decode("latin-1")
            A("    file=0x%07x VA=0x%08x  ctx=%r" % (h, f2v(h) or 0, s))

    # 反汇编 'Chinese GB2312 Texture Loaded' 引用点, 对其做对齐反汇编
    A("\n\n== 对齐反汇编: 'Chinese GB2312 Texture Loaded' (VA 0x8c7e64) 引用点 ==")
    tgt = 0x8C7E64
    text = None
    for s in pe.sections:
        if s.Name.rstrip(b"\x00") == b".text":
            text = s
    t0 = text.PointerToRawData
    code = b[t0:t0 + text.SizeOfRawData]
    cva = base + text.VirtualAddress
    hits = []
    i = 0
    needle = struct.pack("<I", tgt)
    while True:
        j = code.find(needle, i)
        if j < 0:
            break
        hits.append(j)
        i = j + 1
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for h in hits:
        # 向前找对齐起点: 退到最近的 int3 填充后
        s0 = max(0, h - 0x300)
        # 在 s0..h 找 0xCC 连续填充
        seg = code[s0:h]
        k = seg.rfind(b"\xcc\xcc")
        start = s0 + k + 2 if k >= 0 else s0
        A("  ---- 引用 @VA 0x%08x, 反汇编起点 VA 0x%08x ----" % (cva + h, cva + start))
        n = 0
        for ins in md.disasm(code[start:h + 0x140], cva + start):
            mark = " <<<" if ins.address <= cva + h < ins.address + ins.size else ""
            A("    %08x  %-22s %s %s%s" %
              (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
            n += 1
            if n > 400:
                break
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn_load.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written", len(t))


if __name__ == "__main__":
    main()
