#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""pc_cn_font_grid.py -- 解析 PC 中文页 (Chinese0-4.rsb) 的字形网格与索引 (round77 任务 A2/A3)

证据链:
  1. 网格 pitch 自动测量 (行列墨迹投影自相关)
  2. gbtext.def (1288 个 GBK 码, 升序) 与网格槽位顺序对齐 -> 用墨量/结构相关判定
  3. 输出放大裁剪图供目检
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

HDR = {"Chinese%d.rsb" % i: 93 for i in range(5)}


def load_page(name):
    b = open(os.path.join(PC, "Data", "Shell", "Art", name), "rb").read()
    off = HDR.get(name, 93)
    px = np.frombuffer(b[off:off + 512 * 512 * 2], "<u2").reshape(512, 512)
    lo = (px & 0xFF).astype(np.uint8)
    hi = (px >> 8).astype(np.uint8)
    return lo, hi, b


def load_gbdef():
    b = open(os.path.join(PC, "Data", "Shell", "Art", "gbtext.def"), "rb").read()
    return [b[i:i + 2] for i in range(0, len(b) - 1, 2)]


def pitch_profile(img):
    """行/列墨迹投影, 找周期"""
    ink = (img > 8).astype(np.int32)
    rows = ink.sum(1)
    cols = ink.sum(0)
    best = []
    for p in range(8, 40):
        # 周期 p 的匹配度: 空行比例
        s = 0.0
        n = 0
        for k in range(0, 512 - p, p):
            s += abs(int(rows[k]) - int(rows[k + p]))
            n += 1
        best.append((s / max(n, 1), p, "row"))
    return rows, cols, best


def main():
    lo, hi, raw = load_page("Chinese0.rsb")
    gb = load_gbdef()
    L = []
    A = L.append
    A("== Chinese0.rsb 网格分析 ==")
    A("头 93 字节; 表面 = 512x512 u16 LE; 低字节 = 覆盖率")
    ink = (lo > 8)
    A("墨像素 = %d / 262144 (%.2f%%)" % (ink.sum(), 100.0 * ink.mean()))

    rows = ink.sum(1)
    cols = ink.sum(0)
    A("\n-- 行投影为 0 的行号 (最多 60 个) --")
    zr = [i for i in range(512) if rows[i] == 0]
    A("  零墨行 %d 个: %s%s" % (len(zr), zr[:60], " ..." if len(zr) > 60 else ""))
    A("\n-- 列投影为 0 的列号 (最多 60 个) --")
    zc = [i for i in range(512) if cols[i] == 0]
    A("  零墨列 %d 个: %s%s" % (len(zc), zc[:60], " ..." if len(zc) > 60 else ""))

    # 网格周期: 用「整行/整列为空」的间隔推
    def diffs(v):
        if len(v) < 2:
            return []
        return [v[i + 1] - v[i] for i in range(len(v) - 1)]
    A("\n  行零墨间隔直方图: %s" %
      sorted({d: diffs(zr).count(d) for d in set(diffs(zr))}.items(),
             key=lambda x: -x[1])[:10])
    A("  列零墨间隔直方图: %s" %
      sorted({d: diffs(zc).count(d) for d in set(diffs(zc))}.items(),
             key=lambda x: -x[1])[:10])

    # 非空格边界
    nz_row = [i for i in range(512) if rows[i] > 0]
    nz_col = [i for i in range(512) if cols[i] > 0]
    A("\n  最后一行有墨 = %d, 最后一列有墨 = %d" %
      (max(nz_row) if nz_row else -1, max(nz_col) if nz_col else -1))

    # 尝试各种 pitch, 统计「每格四周留白」质量
    A("\n-- pitch 候选 (格数 / 墨像素-格边界冲突) --")
    cands = []
    for pitch in (12, 13, 14, 15, 16, 18, 20, 24, 32):
        n = 512 // pitch
        # 边界行/列应基本无墨
        edge_bad = 0
        for k in range(n):
            y = k * pitch
            x = k * pitch
            edge_bad += int(rows[y]) + int(cols[x])
        cands.append((pitch, n, n * n, edge_bad))
    for pitch, n, slots, bad in cands:
        A("  pitch=%-3d 每维 %d 格, 总 %d 槽, 边界行/列墨合计 = %d" %
          (pitch, n, slots, bad))

    # 输出目检图
    crop = lo[0:64, 0:128]
    Image.fromarray(crop, "L").resize((128 * 6, 64 * 6), Image.NEAREST).save(
        os.path.join(OUT, "cn0_crop_6x.png"))
    Image.fromarray(lo, "L").save(os.path.join(OUT, "cn0_lo.png"))
    A("\n  -> cn0_crop_6x.png (左上 128x64 @6x), cn0_lo.png")

    # gbtext.def 与槽位
    A("\n== gbtext.def ==")
    A("  码数 = %d" % len(gb))
    A("  前 24 个码 = %s" % " ".join(c.hex() for c in gb[:24]))
    A("  后 24 个码 = %s" % " ".join(c.hex() for c in gb[-24:]))
    try:
        A("  前 24 个字 = %s" % "".join(c.decode("gbk") for c in gb[:24]))
        A("  后 24 个字 = %s" % "".join(c.decode("gbk") for c in gb[-24:]))
    except UnicodeDecodeError as e:
        A("  GBK 解码失败: %s" % e)
    # 升序?
    A("  按字节升序 = %s" % (gb == sorted(gb)))
    # 5 页 * 1024 槽 = 5120 vs 1288
    A("  5 页 x 1024 槽 = %d 槽 (码数 %d)" % (5 * 1024, len(gb)))

    # 每页放多少? 看各页墨量
    A("\n== 5 页墨量 ==")
    for i in range(5):
        l2, h2, _ = load_page("Chinese%d.rsb" % i)
        ink2 = (l2 > 8)
        A("  Chinese%d: 墨 %6d (%.2f%%), 非零行 max=%d, 非零列 max=%d" %
          (i, ink2.sum(), 100.0 * ink2.mean(),
           max([y for y in range(512) if ink2[y].any()] or [-1]),
           max([x for x in range(512) if ink2[:, x].any()] or [-1])))
    t = "\n".join(L)
    with io.open(os.path.join(OUT, "pc_cn_font_grid.txt"), "w",
                 encoding="utf-8", newline="\n") as f:
        f.write(t + "\n")
    print(t)


if __name__ == "__main__":
    main()
