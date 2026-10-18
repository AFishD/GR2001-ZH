#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_font_view.py -- 判定 Chinese*.rsb 表面的真实宽高 (round77 任务 A1/A2)

两种候选解读并列渲染, 目检选真。
"""
import io
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def main():
    b = open(os.path.join(PC, "Data", "Shell", "Art", "Chinese0.rsb"), "rb").read()
    px = b[93:93 + 524288]

    # A: 8bpp 1024x512
    a = np.frombuffer(px, np.uint8).reshape(512, 1024)
    Image.fromarray(a, "L").save(os.path.join(OUT, "cn0_as8bpp_1024x512.png"))

    # B: 16bpp 512x512 低字节
    u16 = np.frombuffer(px, "<u2").reshape(512, 512)
    Image.fromarray((u16 & 0xFF).astype(np.uint8), "L").save(
        os.path.join(OUT, "cn0_as16bpp_lo.png"))
    Image.fromarray((u16 >> 8).astype(np.uint8), "L").save(
        os.path.join(OUT, "cn0_as16bpp_hi.png"))

    # 目检裁剪: A 的左上 256x128 @4x
    Image.fromarray(a[0:128, 0:256], "L").resize((256 * 4, 128 * 4),
                                                 Image.NEAREST).save(
        os.path.join(OUT, "cn0_8bpp_crop_4x.png"))
    Image.fromarray((u16[0:128, 0:128] & 0xFF).astype(np.uint8), "L").resize(
        (128 * 4, 128 * 4), Image.NEAREST).save(
        os.path.join(OUT, "cn0_16bpp_crop_4x.png"))
    print("ok")


if __name__ == "__main__":
    main()
