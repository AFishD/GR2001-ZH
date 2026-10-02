# -*- coding: utf-8 -*-
r"""patch_zh65.py — GR_ZH65 = ZH63 + EN 带改用方正像素16 ASCII (用户定案)

用户反馈 (2026-10-03, ZH64 实测): 原版字形提取方案显示效果差, 否决回退原版字库;
ASCII 直接用 16px 像素字体 (与 CJK 同款), 只需位置正确。

方案: 92 个 ASCII (0x21-0x7E 排除 0x7B/0x7D=自绘▲▼) 用 gen_font16 同款渲染管线
(ImageFont.truetype(方正像素16, 16), em 窗 [8:24), 阈值 128), 取半角列窗 [0:8)
原样放入 16 行新带 @v452-467 — 行位 = 字体自身 em 设计 (基线=行13, 与 ZH64 实测
×1 标签 EN 全等的行位一致; 降部最深行15 无裁切), 列位保留轴承。
FT 记录: adv = 8 (0x0800, 字体半角自然步宽), u=(i*8, i*8+8), v=(452,468);
三 face 同步; 空格 adv=8。CJK 格/单字节/▲▼/µ± 零触碰。

用法: python patch_zh65.py <src_iso> <dst_iso>   (基底 = GR_ZH63)
"""
import os
import shutil
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import decode_entry
from ft_dpc import dp_compress

MENU_LBA = 776286
FT_OFF, FT_LEN = 0xB9120, 4421
ENTRY_OFF = 0x58431
REC_LEN = 0x4147D - 0x1031
SEG_LENS = [0x8000] * 7 + [0x7E80]
SEG_Y = [64 * k for k in range(7)] + [448]
BAND_V = 452
ASCII_RANGE = [c for c in range(0x21, 0x7F) if c not in (0x7B, 0x7D)]
ADV = 0x0800                        # 8px 半角步宽


def parse_ft(ft):
    p = 28
    faces = []
    for _ in range(3):
        l = struct.unpack_from('<I', ft, p)[0]
        name = ft[p+4:p+4+l].rstrip(b'\x0a').decode()
        flds = struct.unpack_from('<14i', ft, p+4+l)
        nrec = flds[4] * flds[5]
        q = p + 4 + l + 56
        faces.append({'name': name, 'flds': flds, 'nrec': nrec, 'rec_off': q})
        p = q + nrec * 10
    return faces


def main(src, dst):
    fnt = ImageFont.truetype(os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf'), 16)
    band = np.ones((16, 1024), np.uint8)      # 1 = bg
    for i, c in enumerate(ASCII_RANGE):
        img = Image.new('L', (32, 32), 255)
        d = ImageDraw.Draw(img)
        d.text((8, 8), chr(c), font=fnt, fill=0)
        g = (np.asarray(img)[8:24, 8:24] < 128)[:, :8]     # em 窗半角列, 行位原样
        assert i * 8 + 8 <= 1024
        band[0:16, i*8:(i+1)*8] = np.where(g, 0, 1)
        # 越窗检查: 墨越出半角列窗 [0,8) 的字符 (仅 '~' 超 1px, 截断记录在案)
        full = np.asarray(img)[8:24, 8:24] < 128
        if full[:, 8:].any():
            xs = [j for j, col in enumerate(full.T) if col.any()]
            print(f'  [clip] {chr(c)!r} 墨列 [{xs[0]},{xs[-1]}] 越窗, 截断至 8 列')
    n_ink = int((band == 0).sum())
    print(f'[band] {len(ASCII_RANGE)} 字形 × 8px = {len(ASCII_RANGE)*8} texel, 墨 {n_ink}px, 带 v[{BAND_V},{BAND_V+16})')

    # ── FT 改写 ──
    with open(src, 'rb') as f:
        f.seek(MENU_LBA * 2048 + FT_OFF)
        slot = f.read(FT_LEN)
    ft = bytearray(decode_entry(slot)[0])
    faces = parse_ft(bytes(ft))
    changed = 0
    for fc in faces:
        for i, c in enumerate(ASCII_RANGE):
            off = fc['rec_off'] + (c - 0x20) * 10
            struct.pack_into('<5H', ft, off, ADV, i*8, BAND_V, i*8+8, BAND_V+16)
            changed += 1
        struct.pack_into('<H', ft, fc['rec_off'], ADV)     # 空格 adv=8
    payload = dp_compress(bytes(ft), verbose=False)
    assert len(payload) <= 4413, len(payload)
    frame = struct.pack('<II', len(payload), len(ft)) + payload
    slot2 = frame + b'\x00' * (FT_LEN - len(frame))
    assert decode_entry(slot2)[0] == bytes(ft), 'FT 回环 FAIL'
    print(f'[FT] {changed} 记录 ×3 face + 空格 adv; payload {len(payload)}B ≤ 4413 ✓')

    # ── 字库条目: 新带写入 seg7 ──
    with open(src, 'rb') as f:
        f.seek(MENU_LBA * 2048 + ENTRY_OFF)
        entry = bytearray(f.read(REC_LEN))
    off = 0x43C
    segs = []
    for k in range(8):
        y = struct.unpack_from('<I', entry, off + 20)[0]
        assert y == SEG_Y[k]
        segs.append(off + 48)
        off += 48 + SEG_LENS[k]
    assert BAND_V + 16 <= SEG_Y[7] + SEG_LENS[7] // 512
    for r in range(16):
        ay = BAND_V + r
        k = min(ay // 64, 7)
        rr = ay - SEG_Y[k]
        base = segs[k] + rr * 512
        row = bytearray(entry[base:base+512])
        for x in range(1024):
            v = int(band[r, x])
            if x % 2 == 0:
                row[x//2] = (row[x//2] & 0xF0) | v
            else:
                row[x//2] = (row[x//2] & 0x0F) | (v << 4)
        entry[base:base+512] = row
    print('[entry] 新带 16 行写入 seg7 ✓')

    # ── 写盘 + 断言 ──
    shutil.copyfile(src, dst)
    ft_iso, ent_iso = MENU_LBA*2048+FT_OFF, MENU_LBA*2048+ENTRY_OFF
    with open(dst, 'r+b') as f:
        f.seek(ft_iso); f.write(slot2)
        f.seek(ent_iso); f.write(bytes(entry))
        f.seek(ft_iso); assert f.read(FT_LEN) == slot2
        f.seek(ent_iso); assert f.read(REC_LEN) == bytes(entry)
    a = open(src, 'rb'); b = open(dst, 'rb')
    pos, total = 0, 0
    while True:
        ca, cb = a.read(1 << 20), b.read(1 << 20)
        if not ca:
            break
        for i in range(len(ca)):
            if ca[i] != cb[i]:
                total += 1
                pp = pos + i
                assert (ft_iso <= pp < ft_iso + FT_LEN) or (ent_iso <= pp < ent_iso + REC_LEN), f'窗口外差异 @0x{pp:X}'
        pos += len(ca)
    a.close(); b.close()
    print(f'[diff] 总差异 {total:,}B, 限 FT 槽 ({FT_LEN}B) + 字库条目 ({REC_LEN}B) 两窗口 ✓')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
