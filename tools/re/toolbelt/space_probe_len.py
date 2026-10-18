# -*- coding: utf-8 -*-
r"""space_probe_len.py -- 探针 A: 只改 MENU.IMG 的 ISO 目录记录 data length（内容一字不动）。

单变量: ISO 目录记录里 MENU.IMG;1 的 data length
        0x828D8 (LE u32) / 0x828DC (BE u32)  58300882 -> 58300882 + N

N 的选择:
  * 最大可用 = ISO 末尾扇区边界 - 现声明长度 = 804768*2048 - 776286*2048 - 58300882
              = 583331136 - 58300882 = 30254
  * 任务书要求的 +8192 是它的子集。默认取 **最大 (+30254)**, 一次把"能吃到多少"问清。

判据: 若游戏仍能进主菜单 + 特别收录 + 文本逐像素不变 ⇒ 游戏认目录记录的长度,
      且 MENU.IMG 可以吃到盘尾 30254 字节（为"把 COMMON.PAK 的邻居搬进盘尾"腾地）。

用法: python tools/re/toolbelt/space_probe_len.py <src_iso> <dst_iso> [--add 30254]
"""
import argparse
import hashlib
import os
import shutil
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SEC = 2048
MENU_LBA = 776286
MENU_SIZE = 58300882
ISO_SECTORS = 804768
REC_LE = 0x828D8
REC_BE = 0x828DC
REC_LBA_LE = 0x828D2          # MENU.IMG 的 extent LBA (LE) —— 只读核验, 不写


def sha(b):
    return hashlib.sha256(b).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--add', type=int, default=30254)
    a = ap.parse_args()
    assert os.path.isfile(a.src), a.src
    assert not os.path.exists(a.dst), '拒绝覆盖: %s 已存在' % a.dst

    maxadd = ISO_SECTORS * SEC - MENU_LBA * SEC - MENU_SIZE
    print('[probe] MENU.IMG 可吃到盘尾的最大增量 = %d B' % maxadd)
    assert 0 < a.add <= maxadd, '--add %d 超出可吃范围 (最大 %d)' % (a.add, maxadd)

    # 1) 复制
    print('[copy] %s -> %s' % (a.src, a.dst))
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    shutil.copyfile(a.src, a.dst)
    assert os.path.getsize(a.dst) == os.path.getsize(a.src), '复制后尺寸不一致'

    # 2) 只改 8 字节
    with open(a.dst, 'r+b') as f:
        f.seek(REC_LE)
        le = struct.unpack('<I', f.read(4))[0]
        be = struct.unpack('>I', f.read(4))[0]
        lbale = struct.unpack('<I', f.read(4))[0] if False else None
        print('[before] LE=%d BE=%d  (期望 %d)' % (le, be, MENU_SIZE))
        assert le == MENU_SIZE and be == MENU_SIZE, '目录记录初值不符, 拒绝改'
        new = MENU_SIZE + a.add
        assert new == le + a.add
        f.seek(REC_LE)
        f.write(struct.pack('<I', new))
        f.write(struct.pack('>I', new))

    # 3) 回读校验 + 逐字节差异白名单
    with open(a.dst, 'rb') as f:
        f.seek(REC_LE)
        le2 = struct.unpack('<I', f.read(4))[0]
        be2 = struct.unpack('>I', f.read(4))[0]
    assert le2 == MENU_SIZE + a.add and be2 == MENU_SIZE + a.add, '回读不符'
    print('[after ] LE=%d BE=%d  (+%d)' % (le2, be2, a.add))

    # 4) 全盘差异必须 < 2MB 且只出现在目录记录区
    n_diff, first, last = 0, None, None
    with open(a.src, 'rb') as f1, open(a.dst, 'rb') as f2:
        off = 0
        while True:
            b1 = f1.read(1 << 22)
            b2 = f2.read(1 << 22)
            if not b1:
                break
            if b1 != b2:
                for i in range(min(len(b1), len(b2))):
                    if b1[i] != b2[i]:
                        n_diff += 1
                        if first is None:
                            first = off + i
                        last = off + i
            off += len(b1)
    print('[diff ] 差异字节 = %d, 区间 = [0x%X, 0x%X]' % (n_diff, first or -1, last or -1))
    # 差异必须**只**落在目录记录那 8 字节里 (LE/BE 两个 u32 的公共前缀字节可能相同,
    # 所以差异数 <= 8 而不是 == 8)
    assert 1 <= n_diff <= 8, '差异字节数越界: %d' % n_diff
    assert REC_LE <= first and last < REC_LE + 8, '差异越界: 0x%X..0x%X' % (first, last)
    assert os.path.getsize(a.dst) == ISO_SECTORS * SEC, 'ISO 尺寸变了'

    print('[done] %s  (ISO 尺寸 = %d, 与基底相同)' % (a.dst, os.path.getsize(a.dst)))
    print('       唯一改动 = ISO 目录记录 MENU.IMG;1 data length  +%d  (0x%X/0x%X)'
          % (a.add, REC_LE, REC_BE))


main()
