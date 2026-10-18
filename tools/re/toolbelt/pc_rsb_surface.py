#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_rsb_surface.py -- 按 {mode,w,h,p0..p3} 头假设渲染 PC .rsb 表面 (round77 任务 A1)

头假设:
  {u32 mode}{u32 w}{u32 h}[mode==9: {u32 pad0}]{u32 p0}{u32 p1}{u32 p2}{u32 p3}
  bpp = p0+p1+p2+p3
  表面 = 文件尾 w*h*bpp/8 字节
"""
import io
import os
import struct
import sys

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")
os.makedirs(OUT, exist_ok=True)


def u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def parse(path):
    b = open(path, "rb").read()
    mode = u32(b, 0)
    w = u32(b, 4)
    h = u32(b, 8)
    if mode == 9:
        pad = u32(b, 0x0C)
        ps = [u32(b, 0x10 + 4 * i) for i in range(4)]
        p_be = [struct.unpack_from(">I", b, 0x10 + 4 * i)[0] for i in range(4)]
        hdr_field = ("pad=0x%08x p_le=%s p_be=%s" %
                     (pad, [hex(x) for x in ps], p_be))
        p = p_be
    else:
        p = [u32(b, 0x0C + 4 * i) for i in range(4)]
        hdr_field = "p=%s" % p
    bpp = sum(p)
    pxbytes = w * h * bpp // 8
    off = len(b) - pxbytes
    return dict(data=b, mode=mode, w=w, h=h, p=p, bpp=bpp,
                pxbytes=pxbytes, off=off, size=len(b), hdr=hdr_field)


def show(path, outname=None, cols=None):
    d = parse(path)
    print("%-46s size=%-9d mode=%d w=%-5d h=%-5d bpp=%-3d %s" %
          (os.path.basename(path), d["size"], d["mode"], d["w"], d["h"],
           d["bpp"], d["hdr"]))
    print("    pxbytes=%-9d -> 像素起点 = 0x%x (%d)  头部 = %d 字节" %
          (d["pxbytes"], d["off"], d["off"], d["off"]))
    if d["off"] < 0:
        print("    !! 像素起点为负")
        return None
    b = d["data"][d["off"]:d["off"] + d["pxbytes"]]
    w, h = d["w"], d["h"]
    # 各通道字节视图
    views = {}
    if d["bpp"] == 32:
        a = np.frombuffer(b, np.uint8).reshape(h, w, 4)
        views = {"B": a[:, :, 0], "G": a[:, :, 1], "R": a[:, :, 2], "A": a[:, :, 3]}
    elif d["bpp"] == 24:
        a = np.frombuffer(b, np.uint8).reshape(h, w, 3)
        views = {"B": a[:, :, 0], "G": a[:, :, 1], "R": a[:, :, 2]}
    elif d["bpp"] == 16:
        a = np.frombuffer(b, np.uint8).reshape(h, w, 2)
        u16 = np.frombuffer(b, "<u2").reshape(h, w)
        views = {"lo": a[:, :, 0], "hi": a[:, :, 1]}
        vals, cnts = np.unique(u16, return_counts=True)
        top = sorted(zip(cnts, vals), reverse=True)[:6]
        print("    u16 值 top: %s" % ", ".join("0x%04x×%d" % (v, c) for c, v in top))
        print("    非零 u16 占比 = %.3f" % float((u16 != 0).mean()))
    elif d["bpp"] == 8:
        a = np.frombuffer(b, np.uint8).reshape(h, w)
        views = {"idx": a}
        vals, cnts = np.unique(a, return_counts=True)
        top = sorted(zip(cnts, vals), reverse=True)[:6]
        print("    u8 值 top: %s" % ", ".join("0x%02x×%d" % (v, c) for c, v in top))
    elif d["bpp"] == 4:
        a = np.frombuffer(b, np.uint8)
        lo = (a & 0xF).reshape(h, w // 2)
        hi = (a >> 4).reshape(h, w // 2)
        views = {"lo": lo, "hi": hi}
    for k, v in views.items():
        vals, cnts = np.unique(v, return_counts=True)
        top = sorted(zip(cnts, vals), reverse=True)[:5]
        print("    ch %-3s top=%s" % (k, ", ".join("%d×%d" % (x, c) for c, x in top)))
        if outname:
            Image.fromarray(v.astype(np.uint8), "L").save(
                os.path.join(OUT, "%s_%s.png" % (outname, k)))
    if outname and len(views) > 1:
        # 联系表
        ks = sorted(views)
        sheet = np.zeros((h, w * len(ks)), np.uint8)
        for i, k in enumerate(ks):
            sheet[:, i * w:(i + 1) * w] = views[k]
        Image.fromarray(sheet, "L").save(os.path.join(OUT, outname + "_sheet.png"))
        print("    -> %s_sheet.png  chans=%s" % (outname, ks))
    return d


FILES = [
    "Data/Shell/Art/new_font_revised.rsb",
    "Data/Shell/Art/Chinese0.rsb",
    "Data/Shell/Art/Chinese1.rsb",
    "Data/Shell/Art/gb1200.rsb",
    "Data/Shell/Art/hud.rsb",
    "Data/Shell/Art/cmi.rsb",
    "Data/Shell/Art/load_icon.rsb",
    "Data/Shell/Art/reticle_pistol.rsb",
    "Data/Shell/Art/main_menu-01.rsb",
    "Data/Shell/Art/pda-lcd-02.rsb",
]

if __name__ == "__main__":
    names = sys.argv[1:] or None
    for rel in FILES:
        if names and os.path.basename(rel) not in names:
            continue
        nm = os.path.basename(rel).replace(".rsb", "")
        show(os.path.join(PC, rel), nm)
        print()
