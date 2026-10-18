#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_nfr_view.py -- new_font_revised.rsb 通道视图 (round77 任务 A1)"""
import os
import struct

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
ART = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc",
                   "Data", "Shell", "Art")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")

b = open(os.path.join(ART, "new_font_revised.rsb"), "rb").read()
w = h = 256
a = np.frombuffer(b[43:43 + w * h * 4], np.uint8).reshape(h, w, 4)
for i, cn in enumerate("BGRA"):
    Image.fromarray(a[:, :, i], "L").save(
        os.path.join(OUT, "nfr_ch_%s.png" % cn))
    print("ch %s unique=%d mean=%.1f min=%d max=%d" %
          (cn, len(np.unique(a[:, :, i])), a[:, :, i].mean(),
           a[:, :, i].min(), a[:, :, i].max()))
Image.fromarray(np.concatenate([a[:, :, i] for i in range(4)], 1), "L").save(
    os.path.join(OUT, "nfr_BGRA_sheet.png"))
# pda-lcd-02 for comparison (mode 6 in PS2, here mode 9-ish)
b2 = open(os.path.join(ART, "pda-lcd-02.rsb"), "rb").read()
print("pda-lcd-02 head:", b2[:48].hex())
