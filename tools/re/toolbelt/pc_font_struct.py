#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_font_struct.py -- PC(Ghost Recon 2001) 字体资源结构剖析 (round77 / 任务 A)

只读 third_party/orig/ghost_recon_pc。输出中间产物到
work/builds/GR_ZH98/temp/r77/。

用法:
  python tools/re/toolbelt/pc_font_struct.py hex   <file> [len]   # 十六进制首部
  python tools/re/toolbelt/pc_font_struct.py fontres             # 解析 Data/Shell/font.res
  python tools/re/toolbelt/pc_font_struct.py rsb   <file>         # 判定 rsb 头部
  python tools/re/toolbelt/pc_font_struct.py all                 # 跑全部
"""
import io
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)


def rd(path):
    with open(path, "rb") as f:
        return f.read()


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def i32(b, o):
    return struct.unpack_from("<i", b, o)[0]


def f32(b, o):
    return struct.unpack_from("<f", b, o)[0]


def hexdump(b, off=0, n=256, base=0):
    out = []
    n = min(n, len(b) - off)
    for i in range(off, off + n, 16):
        chunk = b[i:i + 16]
        h = " ".join("%02x" % c for c in chunk)
        a = "".join(chr(c) if 32 <= c < 127 else "." for c in chunk)
        out.append("%08x  %-47s  %s" % (base + i, h, a))
    return "\n".join(out)


def pstr(b, o, maxlen=256):
    """NUL 结尾字符串"""
    e = b.find(b"\x00", o, o + maxlen)
    if e < 0:
        return None, o
    return b[o:e].decode("latin-1"), e + 1


# ---------------------------------------------------------------- font.res

def parse_fontres(path=None, log=None):
    """PC Data/Shell/font.res 解析。

    文件头疑似 RSE 资源封包:
      {u32 type}{char tag[4] 'ike\\0'}{u32 x}  然后接 wire 数据
    """
    path = path or os.path.join(PC, "Data", "Shell", "font.res")
    b = rd(path)
    L = []
    A = L.append
    A("== %s  (%d bytes) ==" % (path, len(b)))
    A(hexdump(b, 0, 128))

    p = 0
    hdr = []
    while True:
        t = u32(b, p)
        if t > 16:
            break
        tag = b[p + 4:p + 8]
        if not all(32 <= c < 127 or c == 0 for c in tag):
            break
        hdr.append((p, t, tag))
        p += 8
        if len(hdr) > 4:
            break
    A("\n-- leading u32/ascii-tag pairs --")
    for off, t, tag in hdr:
        A("  @0x%04x  u32=%d  tag=%r  next u32=0x%08x (%d)" %
          (off, t, tag, u32(b, off + 8), u32(b, off + 8)))

    # 找所有可打印串
    A("\n-- ascii runs (>=4) --")
    i = 0
    runs = []
    while i < len(b):
        if 32 <= b[i] < 127:
            j = i
            while j < len(b) and (32 <= b[j] < 127 or b[j] == 0):
                j += 1
            s = b[i:j]
            if len(s) >= 4:
                runs.append((i, s))
            i = j
        else:
            i += 1
    for off, s in runs:
        A("  @0x%04x  %r" % (off, s))

    # 从纹理名结束处开始按 wire 结构尝试
    txt = None
    for off, s in runs:
        if b"new_font_revised" in s:
            txt = off
            break
    if txt is not None:
        nlen = u32(b, txt - 4)
        wire = txt + nlen
        A("\n-- 纹理名 len=%d, wire 起点 = 0x%04x --" % (nlen, wire))
        A(hexdump(b, wire, 256, 0))
        A("\n-- 按 u32 逐字段(payload) --")
        for k in range(0, 192, 4):
            o = wire + k
            if o + 4 > len(b):
                break
            v = u32(b, o)
            A("  +0x%03x = %-12d 0x%08x  f=%g  %r" %
              (k, v, v, f32(b, o), b[o:o + 4]))
    return "\n".join(L)


# ---------------------------------------------------------------- rsb

def classify_rsb(path, dump=(0, 96)):
    b = rd(path)
    L = []
    name = os.path.basename(path)
    L.append("%-28s size=%-9d sha_head=%s" %
             (name, len(b), b[:8].hex()))
    L.append(hexdump(b, dump[0], dump[1], 0))
    return "\n".join(L)


# ---------------------------------------------------------------- main

def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "hex":
        b = rd(sys.argv[2])
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 256
        print(hexdump(b, 0, n))
        return
    if cmd == "fontres":
        print(parse_fontres())
        return
    if cmd == "rsb":
        print(classify_rsb(sys.argv[2]))
        return
    if cmd == "all":
        t = parse_fontres()
        with io.open(os.path.join(OUT, "pc_fontres_struct.txt"), "w",
                     encoding="utf-8", newline="\n") as f:
            f.write(t + "\n")
        print(t)
        return
    print(__doc__)


if __name__ == "__main__":
    main()
