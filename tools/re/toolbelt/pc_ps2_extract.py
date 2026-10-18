#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_ps2_extract.py -- 解析 PS2 IMG 条目并抽取未压缩样本与 PC 对照 (round77 任务 C)"""
import collections
import io
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PS2ISO = os.path.join(ROOT, "third_party", "orig", "ps2",
                      "Tom Clancy's Ghost Recon (USA).iso")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
SEC = 2048
ENT = 0x830
ENTSZ = 48
NAMEOFF = 0x34CB0


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


def img_entries(path, lba, img_len, nent=6000):
    with open(path, "rb") as f:
        f.seek(lba * SEC)
        head = f.read(min(img_len, 0x500000))
    ents = []
    for i in range(nent):
        o = ENT + ENTSZ * i
        if o + ENTSZ > NAME_OFF_LIMIT:
            break
        f0 = struct.unpack_from("<I", head, o)[0]
        f6, f7, f8 = struct.unpack_from("<III", head, o + 24)
        if f0 == 0xFFFFFFFF or f8 == 0xFFFFFFFF:
            continue
        # 名字
        e = head.find(b"\x00", NAMEOFF + f0)
        if e < 0:
            continue
        nm = head[NAMEOFF + f0:e]
        if not nm or not all(32 <= c < 127 for c in nm):
            continue
        ents.append((nm.decode("latin-1"), f6, f7, f8))
    return ents, head


NAME_OFF_LIMIT = 0x46D60


def main():
    lba, length = iso_lba(PS2ISO, "GR.IMG;1")
    ents, _ = img_entries(PS2ISO, lba, length)
    print("GR.IMG 条目 =", len(ents))
    byext = collections.defaultdict(list)
    for nm, s, r, o in ents:
        byext[os.path.splitext(nm)[1].lower()].append((nm, s, r, o))
    print("\n== 扩展名统计 ==")
    for k, v in sorted(byext.items(), key=lambda x: -len(x[1])):
        print("  %-8s %d" % (k, len(v)))

    print("\n== 未压缩 (stored==real) 样本 ==")
    with open(PS2ISO, "rb") as f:
        for ext in (".atr", ".qob", ".gtf", ".rsb", ".mis", ".txt", ".xml",
                    ".kit", ".gun", ".pob", ".res", ".pak", ".itm", ".kil"):
            lst = byext.get(ext, [])
            if not lst:
                print("  %-6s 无条目" % ext)
                continue
            unc = [x for x in lst if x[1] == x[2]]
            print("  %-6s 共 %-5d 未压缩 %-5d  例: %s" %
                  (ext, len(lst), len(unc),
                   ", ".join("(%s,%d/%d,off=0x%x)" % (n, s, r, o)
                             for n, s, r, o in lst[:3])))
            for n, s, r, o in (unc[:3] or lst[:2]):
                f.seek(lba * SEC + o)
                b = f.read(min(s, 96))
                print("      %-28s off=0x%08x stored=%d real=%d head=%s" %
                      (n, o, s, r, b[:48].hex()))
    return byext


if __name__ == "__main__":
    main()
