# -*- coding: utf-8 -*-
r"""patch_zh63.py — GR_ZH63 = ZH62 + 读卡对话框修复 (ELF 1B + RES 译文两份)

用户报障 (2026-10-02, ZH62 人工测试): 开机 Press Start 后读卡提示屏
① 中文行整体左偏 (左隙 < 右隙); ② 断句在括号中间断开 「(PlayStation®2 / 用)。」+ 多余空格。

── 修复 ①: SWKERN cave trail 极性 (ELF 1 字节) ──
根因: SWKERN cave (0x565670, ZH57 引入/ZH58 迁址) 的 trail 判定分支极性写反:
  0x5656C8: beq t4, zero, +9   (trail >= 0xA1 → 跳 ASCII 单步路径)
真实 pair 的 trail 恒 ∈ [0xA1,0xFE] → t1 恒 0 → kern 仍按字节数计 →
含 CJK 行 StringWidth 高估 kern(=2)×n_pairs → style-3 逐行居中左移 kern×pairs/2。
该 cave 自 ZH57 起对真实字符集等效于 EN 原公式 (no-op), 从未产生预期效果。
修复: beq→bne (0x11800009 → 0x15800009), 仅 1 字节实际变化 (0x11→0x15 @+3)。
实测 (gsrunner, MC 屏 4 行): 修复后 x +8/+10/+11/+17 = kern(2)×pairs/2 精确吻合;
纯 ASCII 串 t1=0 两版一致 → EN 路径零回归 (由构造保证)。

── 修复 ②: G58.I797 译文重写 (MENU + GR 两份 RES) ──
旧译 (71B): 正在读取记忆卡插槽1中的记忆卡(8MB)(PlayStation®2␠用)。请勿取出记忆卡(8MB)。
  - 括号组被折行拆散 + "®2␠用" 中英杂排断裂
新译 (54B): 正在读取记忆卡插槽1中的记忆卡(8MB)。␠请勿取出记忆卡(8MB)。
  - 去掉 (for PlayStation®2) 括注 (读卡语境冗余); 半角空格作折行锚点 → 干净断在句号后
产物: assets_zh63/{menu_res_i797.bin (32,365B), gr_res_i797.bin (32,366B), i797.csv}
  生成: text_replace.py --mode res --charset tools/font_pipeline/data/charset_compiled_zh16.json
        --input i797.csv --base-res <ZH62 现役裁尾基底> --target menu|gr
  (现役基底 = 有效 8 子流帧 + 陈旧尾料, 引擎按子流走读忽略尾料; 新 blob 后余量零填)
布局: MENU #25 @MENU.IMG+0x377E000 槽 47,570B / GR #902 @GR.IMG+0xCAC1750 槽 47,619B
  条目表 off/stored/real 三字段不动 (stored 仍为槽长, 引擎子流走读提前终止)。

用法: python patch_zh63.py <src_iso> <dst_iso>   (经 make_build.py --patch 接入)
"""
import hashlib
import os
import shutil
import struct
import sys

ELF_LBA = 295
VA = 0x5656C8
OLD, NEW = 0x11800009, 0x15800009  # beq t4,zero,+9 -> bne t4,zero,+9

MENU_LBA, GR_LBA = 776286, 19175
RES_WRITES = [
    # (tag, LBA, entry_idx, 槽长, blob 路径, sha256 前 16)
    ('MENU', MENU_LBA, 25, 47570, 'menu_res_i797.bin', '9d1dc2322d4197c5'),
    ('GR', GR_LBA, 902, 47619, 'gr_res_i797.bin', '7bdb961393ef2e18'),
]
HERE = os.path.dirname(os.path.abspath(__file__))


def res_entry(f, lba, idx):
    """读 IMG 条目表: 返回 (name, stored, real, off) — off 为 IMG 内偏移"""
    f.seek(lba * 2048 + 0x10)
    names_off = struct.unpack('<I', f.read(4))[0]
    f.seek(lba * 2048 + 0x830 + 48 * idx + 24)
    stored, real, off = struct.unpack('<III', f.read(12))
    f.seek(lba * 2048 + names_off)
    return stored, real, off


def main(src, dst):
    shutil.copyfile(src, dst)
    windows = []  # (iso_off, expect_old_len) 供 diff 断言

    # ── ① ELF 词 ──
    off = ELF_LBA * 2048 + 0x80 + (VA - 0x100000)
    with open(dst, 'r+b') as f:
        f.seek(off)
        cur = struct.unpack('<I', f.read(4))[0]
        assert cur == OLD, f'0x{VA:X} 现值 0x{cur:08X} != 0x{OLD:08X} (非 ZH62 基底?)'
        f.seek(off)
        f.write(struct.pack('<I', NEW))
        f.seek(off)
        assert struct.unpack('<I', f.read(4))[0] == NEW
    windows.append((off, 4))
    print(f'[ELF] 0x{VA:X}: 0x{OLD:08X} -> 0x{NEW:08X} (beq->bne) ✓')

    # ── ② RES 两份 ──
    with open(dst, 'r+b') as f:
        for tag, lba, idx, slot, fname, sha16 in RES_WRITES:
            blob = open(os.path.join(HERE, 'assets_zh63', fname), 'rb').read()
            assert hashlib.sha256(blob).hexdigest()[:16] == sha16, fname
            assert len(blob) <= slot, (fname, len(blob), slot)
            stored, real, off = res_entry(f, lba, idx)
            iso_off = lba * 2048 + off
            assert stored == slot, (tag, stored, slot)
            f.seek(iso_off)
            old_head = f.read(8)
            assert struct.unpack_from('<II', old_head, 0)[1] in (16384, 13980), old_head.hex()
            f.seek(iso_off)
            f.write(blob)
            f.write(b'\x00' * (slot - len(blob)))       # 余量零填
            f.seek(iso_off)
            back = f.read(slot)
            assert back[:len(blob)] == blob and set(back[len(blob):]) == {0}
            windows.append((iso_off, slot))
            print(f'[RES] {tag} #{idx} @ISO 0x{iso_off:X}: {len(blob)}B + 零填至 {slot}B '
                  f'(条目表 stored={stored} real={real} 不动) ✓')

    # ── 全盘 diff 断言: 差异字节全部落在三个窗口内 ──
    a = open(src, 'rb')
    b = open(dst, 'rb')
    pos, outside, total = 0, 0, 0
    while True:
        ca, cb = a.read(1 << 20), b.read(1 << 20)
        if not ca:
            break
        assert len(ca) == len(cb), '尺寸变化?'
        for i in range(len(ca)):
            if ca[i] != cb[i]:
                total += 1
                p = pos + i
                assert any(w0 <= p < w0 + wl for w0, wl in windows), f'窗口外差异 @0x{p:X}'
        pos += len(ca)
    a.close()
    b.close()
    print(f'[diff] 总差异 {total:,}B, 全部位于 ELF 1B + MENU RES {RES_WRITES[0][3]}B + '
          f'GR RES {RES_WRITES[1][3]}B 三窗口内 ✓')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
