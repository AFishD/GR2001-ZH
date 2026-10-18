#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_qob_diff.py -- PS2 与 PC 同名 .qob/.pob 逐字节对比 (round77 任务 C)"""
import io
import os
import struct

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
PS2ISO = os.path.join(ROOT, "third_party", "orig", "ps2",
                      "Tom Clancy's Ghost Recon (USA).iso")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
SEC = 2048
ENT, ENTSZ, NAMEOFF, LIMIT = 0x830, 48, 0x34CB0, 0x46D60


def entries():
    with open(PS2ISO, "rb") as f:
        f.seek(16 * SEC)
        pvd = f.read(SEC)
    root = pvd[156:156 + 34]
    lba = struct.unpack_from("<I", root, 2)[0]
    size = struct.unpack_from("<I", root, 10)[0]
    with open(PS2ISO, "rb") as f:
        f.seek(lba * SEC)
        d = f.read(size)
    off, img = 0, None
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
        if nm == "GR.IMG;1":
            img = (ext, l)
        off += ln
    with open(PS2ISO, "rb") as f:
        f.seek(img[0] * SEC)
        head = f.read(0x50000)
    es = []
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
        es.append((nm.decode("latin-1"), f6, f7, f8))
    return img[0], es


def main():
    lba, es = entries()
    idx = {n.upper(): (s, r, o) for n, s, r, o in es}
    L = []
    A = L.append
    pairs = [
        ("GRASS_1.QOB", "Mods/Origmiss/Model/grass_1.qob"),
        ("GRASS_2.QOB", "Mods/Origmiss/Model/grass_2.qob"),
        ("DUST.POB", "Mods/Origmiss/Model/dust.pob"),
        ("DEMOLITIONS-01.ATR", "Mods/Origmiss/Actor/demolitions-01.atr"),
    ]
    A("== PS2(GR.IMG) vs PC 同名文件逐字节对比 ==")
    with open(PS2ISO, "rb") as f:
        for nm, rel in pairs:
            p = os.path.join(PC, rel)
            if nm not in idx:
                A("  %-22s PS2 无此条目" % nm)
                continue
            if not os.path.exists(p):
                cand = [os.path.join(dp, fn) for dp, dn, fnn in os.walk(PC)
                        for fn in fnn if fn.lower() == os.path.basename(rel).lower()]
                if not cand:
                    A("  %-22s PC 无 %s" % (nm, rel))
                    continue
                p = cand[0]
            s, r, o = idx[nm]
            f.seek(lba * SEC + o)
            b2 = f.read(s)
            b1 = open(p, "rb").read()
            same = b1 == b2
            A("\n  %s" % nm)
            A("    PC  %-58s %d" % (os.path.relpath(p, PC), len(b1)))
            A("    PS2 (stored=%d real=%d off=0x%x) %d" % (s, r, o, len(b2)))
            A("    逐字节相同 = %s" % same)
            if not same and len(b1) == len(b2):
                d = [i for i in range(len(b1)) if b1[i] != b2[i]]
                A("    差异字节数 = %d / %d, 前 20 处: %s" %
                  (len(d), len(b1), d[:20]))
                A("    PC  head: %s" % b1[:64].hex())
                A("    PS2 head: %s" % b2[:64].hex())
            elif not same:
                n = min(len(b1), len(b2))
                d = [i for i in range(n) if b1[i] != b2[i]]
                A("    长度不同; 前 %d 字节差异 %d 处; 共同前缀 = %d" %
                  (n, len(d), next((i for i in range(n) if b1[i] != b2[i]), n)))
                A("    PC  head: %s" % b1[:64].hex())
                A("    PS2 head: %s" % b2[:64].hex())
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_qob_diff.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
