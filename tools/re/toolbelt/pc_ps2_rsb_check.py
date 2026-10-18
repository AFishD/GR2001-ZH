#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_ps2_rsb_check.py -- 把 PC 侧实测的 RSB 容器模型套到 PS2 的 .RSB 上 (round77 任务 C)

模型: filesize == 43 + w*h*sum(p)/8 + tail,  tail ∈ {38,46,50,66} 由 mode 决定
"""
import collections
import io
import os
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PS2ISO = os.path.join(ROOT, "third_party", "orig", "ps2",
                      "Tom Clancy's Ghost Recon (USA).iso")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
SEC = 2048
ENT = 0x830
ENTSZ = 48
NAMEOFF = 0x34CB0
LIMIT = 0x46D60
TAIL = {4: 38, 5: 46, 6: 50, 9: 66}


def iso_lba(path, name):
    with open(path, "rb") as f:
        f.seek(16 * SEC)
        pvd = f.read(SEC)
    root = pvd[156:156 + 34]
    lba = struct.unpack_from("<I", root, 2)[0]
    size = struct.unpack_from("<I", root, 10)[0]
    with open(path, "rb") as f:
        f.seek(lba * SEC)
        d = f.read(size)
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
        if nm == name:
            return ext, l
        off += ln
    return None, None


def main():
    lba, length = iso_lba(PS2ISO, "GR.IMG;1")
    with open(PS2ISO, "rb") as f:
        f.seek(lba * SEC)
        head = f.read(0x50000)
    ents = []
    for i in range(6000):
        o = ENT + ENTSZ * i
        if o + ENTSZ > LIMIT:
            break
        f0 = struct.unpack_from("<I", head, o)[0]
        f6, f7, f8 = struct.unpack_from("<III", head, o + 24)
        if f0 == 0xFFFFFFFF or f8 == 0xFFFFFFFF:
            continue
        e = head.find(b"\x00", NAMEOFF + f0)
        nm = head[NAMEOFF + f0:e]
        if not nm or not all(32 <= c < 127 for c in nm):
            continue
        ents.append((nm.decode("latin-1"), f6, f7, f8))

    rsbs = [(n, s, r, o) for n, s, r, o in ents
            if n.upper().endswith(".RSB")]
    print("PS2 GR.IMG 的 .RSB 条目 =", len(rsbs))

    L = []
    A = L.append
    A("== PS2 GR.IMG .RSB 条目套用 PC 实测容器模型 ==")
    A("   模型: filesize == 43 + w*h*sum(p)/8 + tail(mode)")
    okn = 0
    stats = collections.Counter()
    bad = []
    with open(PS2ISO, "rb") as f:
        for n, s, r, o in rsbs:
            f.seek(lba * SEC + o)
            b = f.read(min(s, 64))
            if len(b) < 44:
                continue
            mode, w, h = struct.unpack_from("<3I", b, 0)
            if mode == 9:
                p = [struct.unpack_from(">I", b, 0x10 + 4 * i)[0] for i in range(4)]
            else:
                p = [struct.unpack_from("<I", b, 0x0C + 4 * i)[0] for i in range(4)]
            bpp = sum(p)
            need = w * h * bpp // 8
            tail = s - 43 - need
            exp = TAIL.get(mode)
            stats[(mode, tail)] += 1
            if exp is not None and tail == exp and 0 < w <= 2048 and 0 < h <= 2048:
                okn += 1
            else:
                if len(bad) < 12:
                    bad.append((n, s, r, mode, w, h, p, bpp, need, tail, exp))
    A("  条目 %d, 模型命中 %d (%.1f%%)" % (len(rsbs), okn,
                                        100.0 * okn / max(len(rsbs), 1)))
    A("\n  (mode, tail) 直方图 top:")
    for (m, t), c in stats.most_common(14):
        A("    mode=%-2d tail=%-6d %d 次   [期望 mode%d tail=%s]" %
          (m, t, c, m, TAIL.get(m)))
    A("\n  未命中前 12 例:")
    for n, s, r, mode, w, h, p, bpp, need, tail, exp in bad:
        A("    %-30s size=%-9d mode=%d %dx%d p=%s bpp=%d need=%d tail=%d (期望 %s)" %
          (n, s, mode, w, h, str(p), bpp, need, tail, exp))

    # 抽 2 个 PS2 rsb 完整校验
    A("\n== 抽 3 个模式 5/6 的 PS2 .RSB 逐字节校验 ==")
    with open(PS2ISO, "rb") as f:
        for n, s, r, o in rsbs:
            f.seek(lba * SEC + o)
            b = f.read(s)
            mode, w, h = struct.unpack_from("<3I", b, 0)
            if mode not in (5, 6):
                continue
            p = [struct.unpack_from("<I", b, 0x0C + 4 * i)[0] for i in range(4)]
            need = w * h * sum(p) // 8
            tail = len(b) - 43 - need
            A("  %-28s mode=%d %dx%d p=%s bpp=%d  43+%d+%d=%d vs 实际 %d  %s" %
              (n, mode, w, h, str(p), sum(p), need, tail, 43 + need + tail,
               len(b), "OK" if tail == TAIL[mode] else "tail=" + str(tail)))
            A("      head=%s" % b[:32].hex())
            if sum(1 for _ in ()) > 0:
                break
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_ps2_rsb_check.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
