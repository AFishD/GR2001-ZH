#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_dis.py -- 反汇编 GhostRecon.exe 里 RSB 加载器与中文字体加载 (round77 任务 A/D)

用 capstone + pefile。找引用指定字符串 VA 的代码并反汇编上下文。
"""
import io
import os
import struct
import sys

import capstone
import pefile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)

STRINGS_FILEOFF = [
    (0x04BF494, "Error reading rsb header."),
    (0x04BF4B0, "RSB: "),
    (0x04BF574, " as a .RSBMP file"),
    (0x04BF5AC, ".rsb"),
    (0x04C7E3B, "@Chinese BIG5 Texture Loaded"),
    (0x04C7E64, "Chinese GB2312 Texture Loaded"),
    (0x04D35B4, "Chinese Font load succeeded!!!"),
    (0x04C10F0, "\\data\\shell\\fonts"),
    (0x04B690C, "font.res"),
    (0x04B68F4, "strings.res"),
    (0x04B6A94, "\\strings.txt"),
    (0x04C0594, "RSUIMgr::Initialize: Font manager initialized"),
]


def main():
    exe = os.path.join(PC, "GhostRecon.exe")
    pe = pefile.PE(exe, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    print("ImageBase = 0x%x" % base)
    text = None
    for s in pe.sections:
        nm = s.Name.rstrip(b"\x00").decode()
        print("  %-10s VA=0x%08x vsz=0x%x raw=0x%x ptr=0x%x" %
              (nm, base + s.VirtualAddress, s.Misc_VirtualSize,
               s.SizeOfRawData, s.PointerToRawData))
        if nm == ".text":
            text = s
    tb = open(exe, "rb").read()
    t0 = text.PointerToRawData
    t1 = t0 + text.SizeOfRawData
    code = tb[t0:t1]
    code_va = base + text.VirtualAddress

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False

    def foff2va(f):
        for s in pe.sections:
            p = s.PointerToRawData
            if p <= f < p + s.SizeOfRawData:
                return base + s.VirtualAddress + (f - p)
        return None

    L = []
    A = L.append
    for fo, s in STRINGS_FILEOFF:
        va = foff2va(fo)
        A("=" * 90)
        A("### 字符串 file=0x%08x VA=0x%08x  %r" % (fo, va or 0, s))
        if va is None:
            A("  (不在任何节内)")
            continue
        needle = struct.pack("<I", va)
        hits = []
        i = 0
        while True:
            j = code.find(needle, i)
            if j < 0:
                break
            hits.append(j)
            i = j + 1
        A("  引用点 %d 个: %s" %
          (len(hits), " ".join("VA 0x%x" % (code_va + h) for h in hits[:20])))
        for h in hits[:6]:
            start = max(0, h - 0x80)
            end = min(len(code), h + 0xA0)
            A("  ---- 上下文 @VA 0x%08x ----" % (code_va + h))
            for ins in md.disasm(code[start:end], code_va + start):
                mark = " <<<" if ins.address <= code_va + h < ins.address + ins.size else ""
                A("    %08x  %-24s %s %s%s" %
                  (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str, mark))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_rsb_dis.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print("written", len(t))


if __name__ == "__main__":
    main()
