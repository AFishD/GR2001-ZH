#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_font_measure.py -- 精确测定 Chinese*.rsb 的格子周期 (round77 任务 A1/A2/A3)"""
import io
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PC = os.path.join(ROOT, "third_party", "orig", "ghost_recon_pc")
OUT = os.path.join(ROOT, "work", "builds", "GR_ZH98", "temp", "r77")


def main():
    b = open(os.path.join(PC, "Data", "Shell", "Art", "Chinese0.rsb"), "rb").read()
    px = np.frombuffer(b[93:93 + 524288], np.uint8)

    L = []
    A = L.append

    # --- 说法 1: 8bpp 1024x512
    a = px.reshape(512, 1024)
    ink = (a > 8).astype(np.int32)
    rows = ink.sum(1)
    cols = ink.sum(0)
    A("== 8bpp 1024x512 解读 ==")
    A("  墨像素 %d (%.2f%%)" % (ink.sum(), 100.0 * ink.mean()))
    A("  行投影: 零行 %d, 非零行范围 [%d,%d]" %
      (int((rows == 0).sum()), int(np.argmax(rows > 0)),
       int(511 - np.argmax(rows[::-1] > 0))))
    A("  列投影: 零列 %d, 非零列范围 [%d,%d]" %
      (int((cols == 0).sum()), int(np.argmax(cols > 0)),
       int(1023 - np.argmax(cols[::-1] > 0))))

    # 自相关找周期: 对列投影, 求 lag 的自相关峰值
    def periods(proj, maxp=64):
        p = proj - proj.mean()
        res = []
        for lag in range(6, maxp + 1):
            v = float((p[:-lag] * p[lag:]).mean())
            res.append((v, lag))
        res.sort(reverse=True)
        return res[:8]

    A("  列投影自相关 top-lag: %s" %
      ", ".join("lag%d=%.0f" % (l, v) for v, l in periods(cols)))
    A("  行投影自相关 top-lag: %s" %
      ", ".join("lag%d=%.0f" % (l, v) for v, l in periods(rows)))

    # --- 说法 2: 16bpp 512x512
    u16 = np.frombuffer(b[93:93 + 524288], "<u2").reshape(512, 512)
    lo = (u16 & 0xFF).astype(np.uint8)
    ink2 = (lo > 8).astype(np.int32)
    rows2 = ink2.sum(1)
    cols2 = ink2.sum(0)
    A("\n== 16bpp 512x512 (低字节) 解读 ==")
    A("  墨像素 %d (%.2f%%)" % (ink2.sum(), 100.0 * ink2.mean()))
    A("  行投影自相关 top-lag: %s" %
      ", ".join("lag%d=%.0f" % (l, v) for v, l in periods(rows2)))
    A("  列投影自相关 top-lag: %s" %
      ", ".join("lag%d=%.0f" % (l, v) for v, l in periods(cols2)))

    # --- 逐格墨量: 假设 8bpp 1024x512 且格 32x32
    for (cw, ch, W, H, src, tag) in ((32, 32, 1024, 512, a, "8bpp/1024x512/cell32"),
                                     (16, 32, 1024, 512, a, "8bpp/1024x512/cell16x32"),
                                     (16, 16, 512, 512, lo, "16bpp/512x512/cell16")):
        nc, nr = W // cw, H // ch
        # 计算每格四周 1px 空白率 与 每格内部墨量分布
        cnt = np.zeros((nr, nc), np.int32)
        for r in range(nr):
            for c in range(nc):
                cnt[r, c] = int((src[r * ch:(r + 1) * ch, c * cw:(c + 1) * cw] > 8).sum())
        nz = cnt[cnt > 0]
        A("\n  [%s] 格 %dx%d, 共 %dx%d=%d 槽; 非空格 %d (%.1f%%); 每格墨量 min/med/max = %d/%d/%d" %
          (tag, cw, ch, nc, nr, nc * nr, len(nz), 100.0 * len(nz) / (nc * nr),
           nz.min() if len(nz) else -1, int(np.median(nz)) if len(nz) else -1,
           nz.max() if len(nz) else -1))

    # --- 单字放大: 8bpp 前 4x2 格
    for i in range(4):
        c0 = a[0:32, i * 32:(i + 1) * 32]
        Image.fromarray(c0, "L").resize((32 * 10, 32 * 10), Image.NEAREST).save(
            os.path.join(OUT, "cell_8bpp_%d.png" % i))
    A("\n  -> cell_8bpp_0..3.png (8bpp 前 4 格 @10x)")

    # --- 页首字 = gbtext.def[0] = A3A1 '！' ?
    A("\n== 首格 vs gbtext.def[0] = A3A1 (！) 目检用图已存 ==")
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn_font_measure.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
