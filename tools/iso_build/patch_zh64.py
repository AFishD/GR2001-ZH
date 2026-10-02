# -*- coding: utf-8 -*-
r"""patch_zh64.py — GR_ZH64 = ZH63 + EN 带重铺 (原版字形恢复)

问题 (2026-10-02 用户报障): 训练 1 瞄准镜缩放读数条倍数标签 (x4/x1) 字形细碎 + 偏上。
根因 (本轮定案): 现役 EN 带 (ASCII 98 码位, v376-411) = 13px 时代 Zpix 迷你字形
(7px 等宽、~5×9 细笔画、墨迹贴记录窗顶部), 16px 时代原样继承 — 与 EN 原版
(11×13 实心字母、比例宽度、基线贴底) 相比又小又细又高。
(+4 采样错位假说已用判定盘证伪: EN 带右移 4 texel 后仍碎, 只是碎法不同。)

修复: 用 EN 原版 large 面字形重铺 —
  1. 从 EN 原版字库 (docs/han_v2/artifacts/COMMON_PAK.bin 内 new_font_revised,
     PSMT8 512×512) 取 95 个 ASCII 字形 (0x21-0x7E, 排除 0x7B/0x7D=自绘▲▼);
  2. 墨迹 bbox 裁切 (ink = texel<24, 54+ 为背景噪声), 底对齐放入 16 行新带 @v452
     (caps 底=行13 与 CJK 基线协同; 降部字延伸到行15; 超高字裁顶);
  3. FT 记录同步改写: adv 恢复原版比例宽度, u/v 指向新带 (三 face 同步);
  4. 空格 adv 恢复 3072 (12px); ▲▼/µ± (0x7B/0x7D/0xB1/0xB5) 不动。
预期: 全游戏 ASCII (x4/x1、TEQSUNSET、(8MB)、START) = EN 原版字形观感;
ASCII 串宽变化 (adv 7→4~19) → 居中/折行按 EN 比例重排。

用法: python patch_zh64.py <src_iso> <dst_iso>
"""
import os
import shutil
import struct
import sys

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
BAND_V = 452                     # 新 EN 带 (16 行, 空白区, 避开 slot1426 横杠 y425/426)
INK_THR = 24
ASCII_RANGE = [c for c in range(0x21, 0x7F) if c not in (0x7B, 0x7D)]


def parse_ft(ft):
    """{28B 头}{face: {u32 namelen}{name}{14×u32}{nrec×10B}}*3"""
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
    return faces, p


def main(src, dst):
    # ── 源材料 1: EN 原版字库 (容器工件) ──
    pak = open(os.path.join(REPO, 'docs', 'han_v2', 'artifacts', 'COMMON_PAK.bin'), 'rb').read()
    p = 0x1031
    flag, nl = struct.unpack_from('<II', pak, p)
    assert pak[p+8:p+8+nl].split(b'\0')[0] == b'new_font_revised'
    q = p + 8 + nl
    psm, w, h, clut_size = struct.unpack_from('<IIII', pak, q)
    assert (psm, w, h) == (19, 512, 512)
    q += 16 + clut_size
    px_size = struct.unpack_from('<I', pak, q)[0]
    px = pak[q+4+16:q+4+px_size]
    assert len(px) == 512 * 512
    orig = list(px)

    # ── 源材料 2: EN 原版 FT (large 面 ASCII 记录) ──
    en_iso = open(os.path.join(REPO, 'third_party', 'orig', 'ps2', "Tom Clancy's Ghost Recon (USA).iso"), 'rb')
    en_iso.seek(MENU_LBA * 2048 + FT_OFF)
    en_ft = bytes(decode_entry(en_iso.read(FT_LEN))[0])
    en_faces, _ = parse_ft(en_ft)
    lf = [f for f in en_faces if f['name'] == 'large'][0]
    en_recs = {}
    for c in ASCII_RANGE:
        adv, u0, v0, u1, v1 = struct.unpack_from('<5H', en_ft, lf['rec_off'] + (c-0x20)*10)
        en_recs[c] = (adv, u0, v0, u1, v1)
    sp_adv = struct.unpack_from('<5H', en_ft, lf['rec_off'])[0]

    # ── 新带布局: bbox 裁切 + 水平排布 ──
    band = [[1] * 1024 for _ in range(16)]        # 1 = bg
    new_recs = {}
    dx = 0
    for c in ASCII_RANGE:
        adv, u0, v0, u1, v1 = en_recs[c]
        mask = [( [orig[y*512+x] < INK_THR for x in range(u0, u1)]) for y in range(v0, v1)]
        rows = [i for i, r in enumerate(mask) if any(r)]
        if not rows:
            print(f'  [warn] {chr(c)!r} 原版无墨, 保留现记录')
            continue
        r0, r1 = rows[0], rows[-1]
        cols = [j for j in range(u1-u0) if any(mask[r][j] for r in range(r0, r1+1))]
        c0, c1 = cols[0], cols[-1]
        hh, ww = r1-r0+1, c1-c0+1
        # 底对齐基线 = 行15 (=16px 格底, 与 CJK 基线协同; 缩放标签路径按实测校准落 EN 位):
        # h≤16 → [16-h, 15]; h>16 裁顶
        bottom = 15
        top = max(0, 16 - hh)
        clip = hh - (bottom - top + 1)
        assert dx + ww <= 1024, f'新带溢出 @ {chr(c)!r} dx={dx}'
        for yy in range(top, bottom + 1):
            sy = r0 + clip + (yy - top)
            for xx in range(ww):
                band[yy][dx+xx] = 1 if not mask[sy][c0+xx] else 0
        new_recs[c] = (adv, dx, BAND_V, dx+ww, BAND_V+16)
        dx += ww + 1
    print(f'[band] {len(new_recs)} 字形, 宽 {dx} texel, 带 v[{BAND_V},{BAND_V+16})')

    # ── 改 FT: 三 face ASCII 记录 + 空格 adv ──
    with open(src, 'rb') as f:
        f.seek(MENU_LBA * 2048 + FT_OFF)
        slot = f.read(FT_LEN)
    ft = bytearray(decode_entry(slot)[0])
    faces, _tail = parse_ft(bytes(ft))   # _tail = styles 段起点, 不触碰
    changed = 0
    for fc in faces:
        for c, (adv, u0, v0, u1, v1) in new_recs.items():
            off = fc['rec_off'] + (c - 0x20) * 10
            struct.pack_into('<5H', ft, off, adv, u0, v0, u1, v1)
            changed += 1
        struct.pack_into('<H', ft, fc['rec_off'], sp_adv)  # 空格 adv
    payload = dp_compress(bytes(ft), verbose=False)
    assert len(payload) <= 4413, len(payload)
    frame = struct.pack('<II', len(payload), len(ft)) + payload
    slot2 = frame + b'\x00' * (FT_LEN - len(frame))
    assert decode_entry(slot2)[0] == bytes(ft), 'FT 回环 FAIL'
    print(f'[FT] {changed} 记录改写 ×3 face + 空格 adv; payload {len(payload)}B ≤ 4413 ✓')

    # ── 改字库条目: 新带 texel 写入 seg7 ──
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
            v = band[r][x]
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
    W1, W2 = 512, 0
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
