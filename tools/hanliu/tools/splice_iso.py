#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: gr_tools/splice_iso.py (逐字复制 (MENU 原位拼接, LBA 776286))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""splice_iso.py - 把同尺寸 MENU.IMG 原位拼接进原盘 ISO (唯一验证可行的组装方式)

原盘 MENU.IMG: LBA 776286, 长度 58,300,882 (28,466 扇区)
用法: python splice_iso.py <原盘iso> <menu.img> <输出iso> [lba]
"""
import sys, os

SRC, MENU, DST = sys.argv[1], sys.argv[2], sys.argv[3]
LBA = int(sys.argv[4]) if len(sys.argv) > 4 else 776286
SECTOR = 2048

menu = open(MENU, 'rb').read()
src_size = os.path.getsize(SRC)
expect = sys.argv[5] if len(sys.argv) > 5 else None
if expect and len(menu) != int(expect):
    raise SystemExit('尺寸 %d != 期望 %s' % (len(menu), expect))
if len(menu) % SECTOR and (src_size - (LBA * SECTOR + len(menu))) < SECTOR:
    pass  # 非对齐尾部允许: 输出尺寸断言兜底

with open(SRC, 'rb') as src, open(DST, 'wb') as dst:
    target = LBA * SECTOR
    remain = src_size
    # 逐段复制: [0, target) → MENU → [target+len(menu), end)
    chunk = 1 << 22
    pos = 0
    while pos < target:
        n = min(chunk, target - pos)
        dst.write(src.read(n)); pos += n
    dst.write(menu)                                        # 覆盖原 MENU 区
    src.seek(target + len(menu))
    pos = target + len(menu)
    while pos < src_size:
        n = min(chunk, src_size - pos)
        dst.write(src.read(n)); pos += n
print('完成: %s = %d 字节 (原盘 %d)' % (DST, os.path.getsize(DST), src_size))
assert os.path.getsize(DST) == src_size, '输出尺寸与原盘不一致!'
