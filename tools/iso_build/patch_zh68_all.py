# -*- coding: utf-8 -*-
r"""patch_zh68_all.py — GR_ZH68 合并构筑 (ZH62 → 终态一步到位)

合并 ZH63-ZH68 五轮有效修改 (ZH64 原版字形方案 / ZH65 无留空像素字方案均被否决, 不含):
  ① SWKERN trail 极性 1B (0x5656C8 beq→bne, kern 按字形计数)                    [ZH63]
  ② G58.I797 译文重写 (MENU #25 + GR #902 双份 RES, 条目表不动)                 [ZH63]
  ③ 字库 EN 带方正像素16 重铺 (92 ASCII + 8px 步宽 + 采样窗顶留空 2 行)          [ZH66]
  ④ 帮助条 style-0x52 手术 (hook 0x21CA50 + cave 0x565730, y+4)                 [ZH67+68]

逐项详见 docs/PATCH_INVENTORY.md §八/§十/§十一/§十二/§十三 与 docs/PROGRESS.md §27-32。
验证: 产物与增量链 (ZH63→66→67→68) 构筑的 GR_ZH68.iso 逐字节相等 (sha256 一致)。

用法: python patch_zh68_all.py <src_iso> <dst_iso>   (基底 = work/builds/GR_ZH62)
"""
import hashlib
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

ELF_LBA, MENU_LBA, GR_LBA = 295, 776286, 19175
SWKERN_VA, SWKERN_OLD, SWKERN_NEW = 0x5656C8, 0x11800009, 0x15800009
HOOK_VA, HOOK_OLD, HOOK_NEW = 0x21CA50, 0xAC8300EC, 0x081595CC
CAVE_VA = 0x565730
CAVE = [0x8C88003C, 0x8C8A004C, 0x010A4021, 0x8C890014, 0x312900FF,
        0x240A0052, 0x152A0002, 0x00000000, 0x25080004, 0xAC8800EC,
        0x08087296, 0x00000000]
RES_WRITES = [
    ('MENU', MENU_LBA, 25, 47570, 'menu_res_i797.bin', '9d1dc2322d4197c5'),
    ('GR',   GR_LBA, 902, 47619, 'gr_res_i797.bin', '7bdb961393ef2e18'),
]
FT_OFF, FT_LEN, ENTRY_OFF, REC_LEN = 0xB9120, 4421, 0x58431, 0x4147D - 0x1031
SEG_LENS = [0x8000] * 7 + [0x7E80]
SEG_Y = [64 * k for k in range(7)] + [448]
BAND_V, REC_V0, ADV = 452, 450, 0x0800
ASCII_RANGE = [c for c in range(0x21, 0x7F) if c not in (0x7B, 0x7D)]


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


def res_entry(f, lba, idx):
    f.seek(lba * 2048 + 0x10)
    names_off = struct.unpack('<I', f.read(4))[0]
    f.seek(lba * 2048 + 0x830 + 48 * idx + 24)
    stored, real, off = struct.unpack('<III', f.read(12))
    f.seek(lba * 2048 + names_off)
    return stored, real, off


def main(src, dst):
    shutil.copyfile(src, dst)
    win = []
    with open(dst, 'r+b') as f:
        # ── ① SWKERN 1B ──
        off = ELF_LBA * 2048 + 0x80 + (SWKERN_VA - 0x100000)
        f.seek(off)
        cur = struct.unpack('<I', f.read(4))[0]
        assert cur == SWKERN_OLD, f'SWKERN 现值 0x{cur:08X}'
        f.seek(off)
        f.write(struct.pack('<I', SWKERN_NEW))
        win.append((off, 4))
        print('[1] SWKERN 0x5656C8 beq→bne')

        # ── ② I797 双份 RES ──
        for tag, lba, idx, slot, fname, sha16 in RES_WRITES:
            blob = open(os.path.join(HERE, 'assets_zh63', fname), 'rb').read()
            assert hashlib.sha256(blob).hexdigest()[:16] == sha16, fname
            assert len(blob) <= slot
            stored, real, off = res_entry(f, lba, idx)
            iso_off = lba * 2048 + off
            assert stored == slot, (tag, stored, slot)
            f.seek(iso_off)
            old_head = f.read(8)
            assert struct.unpack_from('<II', old_head, 0)[1] in (16384, 13980), old_head.hex()
            f.seek(iso_off)
            f.write(blob)
            f.write(b'\x00' * (slot - len(blob)))
            f.seek(iso_off)
            back = f.read(slot)
            assert back[:len(blob)] == blob and set(back[len(blob):]) == {0}
            win.append((iso_off, slot))
            print(f'[2] {tag} #{idx} I797 重编码 {len(blob)}B+零填')

        # ── ③ EN 带像素16 重铺 (含采样窗顶留空 2 行) ──
        fnt = ImageFont.truetype(os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf'), 16)
        band = np.ones((16, 1024), np.uint8)
        for i, c in enumerate(ASCII_RANGE):
            img = Image.new('L', (32, 32), 255)
            ImageDraw.Draw(img).text((8, 8), chr(c), font=fnt, fill=0)
            g = (np.asarray(img)[8:24, 8:24] < 128)[:, :8]
            band[0:16, i*8:(i+1)*8] = np.where(g, 0, 1)
        f.seek(MENU_LBA * 2048 + FT_OFF)
        slot = f.read(FT_LEN)
        ft = bytearray(decode_entry(slot)[0])
        faces = parse_ft(bytes(ft))
        changed = 0
        for fc in faces:
            for i, c in enumerate(ASCII_RANGE):
                struct.pack_into('<5H', ft, fc['rec_off'] + (c - 0x20) * 10,
                                 ADV, i*8, REC_V0, i*8+8, REC_V0+16)
                changed += 1
            struct.pack_into('<H', ft, fc['rec_off'], ADV)
        payload = dp_compress(bytes(ft), verbose=False)
        assert len(payload) <= 4413, len(payload)
        frame = struct.pack('<II', len(payload), len(ft)) + payload
        slot2 = frame + b'\x00' * (FT_LEN - len(frame))
        assert decode_entry(slot2)[0] == bytes(ft), 'FT 回环 FAIL'
        ft_iso = MENU_LBA * 2048 + FT_OFF
        f.seek(ft_iso)
        f.write(slot2)
        win.append((ft_iso, FT_LEN))
        f.seek(MENU_LBA * 2048 + ENTRY_OFF)
        entry = bytearray(f.read(REC_LEN))
        off = 0x43C
        segs = []
        for k in range(8):
            y = struct.unpack_from('<I', entry, off + 20)[0]
            assert y == SEG_Y[k]
            segs.append(off + 48)
            off += 48 + SEG_LENS[k]
        for r in range(16):
            ay = BAND_V + r
            k = min(ay // 64, 7)
            base = segs[k] + (ay - SEG_Y[k]) * 512
            row = bytearray(entry[base:base+512])
            for x in range(1024):
                v = int(band[r, x])
                row[x//2] = (row[x//2] & 0xF0) | v if x % 2 == 0 else (row[x//2] & 0x0F) | (v << 4)
            entry[base:base+512] = row
        ent_iso = MENU_LBA * 2048 + ENTRY_OFF
        f.seek(ent_iso)
        f.write(bytes(entry))
        win.append((ent_iso, REC_LEN))
        print(f'[3] EN 带 {len(ASCII_RANGE)} 字形像素16 + FT {changed} 记录 ×3 + 新带 @v{BAND_V} (窗 v{REC_V0})')

        # ── ④ 帮助条 style-0x52 手术 (+4) ──
        ho = ELF_LBA * 2048 + 0x80 + (HOOK_VA - 0x100000)
        co = ELF_LBA * 2048 + 0x80 + (CAVE_VA - 0x100000)
        f.seek(ho)
        cur = struct.unpack('<I', f.read(4))[0]
        assert cur == HOOK_OLD, f'hook 现值 0x{cur:08X}'
        f.seek(co)
        assert f.read(4 * len(CAVE)) == b'\x00' * 4 * len(CAVE), 'cave 区非零'
        f.seek(ho)
        f.write(struct.pack('<I', HOOK_NEW))
        f.seek(co)
        f.write(b''.join(struct.pack('<I', w) for w in CAVE))
        f.seek(ho)
        assert struct.unpack('<I', f.read(4))[0] == HOOK_NEW
        win.append((ho, 4))
        win.append((co, 4 * len(CAVE)))
        print('[4] 帮助条手术 hook 0x21CA50 + cave 0x565730 (y+4)')

    # ── 全盘 diff 断言 (按预期词集) ──
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, words = 0, set()
    while True:
        x, y = a.read(1 << 20), b.read(1 << 20)
        if not x:
            break
        for i in range(len(x)):
            if x[i] != y[i]:
                words.add((pos + i) & ~3)
        pos += len(x)
    a.close(); b.close()
    def in_win(p):
        return any(o <= p < o + l for o, l in win)
    bad = [w for w in words if not in_win(w)]
    assert not bad, f'窗口外差异词: {[hex(x) for x in bad[:5]]}'
    print(f'[diff] 差异词 {len(words)} 个, 全部位于 {len(win)} 个声明窗口内 ✓')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
