# -*- coding: utf-8 -*-
r"""shift.py — 字库链阶段 5: 每行左移 2B (=4 texel, 图标带豁免) + slot1426 横杠

提取自 build_zh38_final.py (归档分支 work/zh16b/subagent_root2/, GR_ZH38 终盘) 的现役变换。
输入: work/builds/GR_ZH62/font_out/common_pak_seg_tmp.bin (make_pak 阶段 4 产物)
输出: work/builds/GR_ZH62/font_out/font_entry_zh62.bin (条目域 [0x1031,0x4147D), 可直写 MENU.IMG @0x58431)
自检: 与 work/builds/GR_ZH62/GR_ZH62.iso 现役条目对比, 预期残差 = 1B NLOOP (ZH49) + ~88B EN 带微调。
"""
import os, struct

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
IN = os.path.join(REPO, 'work', 'builds', 'GR_ZH62', 'font_out', 'common_pak_seg_tmp.bin')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH62', 'font_out', 'font_entry_zh62.bin')
REC, REC_LEN = 0x1031, 0x4147D - 0x1031
SEG_LENS = [0x8000] * 7 + [0x7E80]
SEG_Y = [64 * k for k in range(7)] + [448]
ICON_BAND = (196, 224)
PAD = 0x11

rep = bytearray(open(IN, 'rb').read()[REC:REC + REC_LEN])
off = 0x43C  # px tag = 首段 PT 包头
segs = []
for k in range(8):
    w0, w1 = struct.unpack_from('<II', rep, off)
    y = struct.unpack_from('<I', rep, off + 20)[0]
    w0b, w1b = struct.unpack_from('<II', rep, off + 32)
    assert w0 == 1 and w1 == 0x10000000 and struct.unpack_from('<Q', rep, off + 24)[0] == 0x52
    assert y == SEG_Y[k] and w1b == 0x08000000 and (w0b & 0x7FFF) * 16 == SEG_LENS[k]
    segs.append(off)
    off += 48 + SEG_LENS[k]
assert off == 0x43C + 0x40000

for k in range(8):
    doff = segs[k] + 48
    L = SEG_LENS[k]
    for r in range(L // 512):
        ay = SEG_Y[k] + r
        if ICON_BAND[0] <= ay < ICON_BAND[1]:
            continue
        base = doff + r * 512
        rep[base:base + 512] = rep[base + 2:base + 512] + bytes([PAD, PAD])
    if L % 512:
        base = doff + (L // 512) * 512
        rep[base:base + L % 512] = rep[base + 2:base + L % 512] + bytes([PAD, PAD])

# slot1426 真空位横杠 (build_zh38_final 终盘): 墨窗 x[4,20) y[418,434) 第 7-8 行
for ay in (418 + 7, 418 + 8):
    k = min(ay // 64, 7)
    r_in = ay - SEG_Y[k]
    doff = segs[k] + 48 + r_in * 512
    for b in range(8):
        rep[doff + 4 // 2 + b] = 0x00

open(OUT, 'wb').write(bytes(rep))
iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH62', 'GR_ZH62.iso')
if os.path.exists(iso):
    f = open(iso, 'rb')
    f.seek(776286 * 2048 + 0x58431)
    shipped = f.read(REC_LEN)
    d = sum(1 for a, b in zip(shipped, rep) if a != b)
    print('[OK] font_entry_zh62.bin 写出; vs 现役 ZH62 差异 %dB (预期 89 = 1B NLOOP + 88B EN 带微调)' % d)
else:
    print('[OK] font_entry_zh62.bin 写出 (现役盘不在, 跳过对照)')
