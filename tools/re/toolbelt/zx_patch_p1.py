# -*- coding: utf-8 -*-
r"""zx_patch_p1.py — P1 单变量探针补丁 (make_build 的 `--patch` 入口)

    python zx_patch_p1.py <src.iso> <dst.iso>
    ⇔ zx_patch_font.py --p1 <src.iso> <dst.iso>

P1 只改数据侧: COMMON.PAK 的 h 512→640 / px_size 0x40010→0x501F0 / 容器重切成 10 段
（行 0..510 逐字节复制, 新行 512..639 填 0x11）+ COMMON.PAK 长大 66,016 + MENU.IMG 平移
+ ISO9660 目录记录长度。**FONT.RES / ELF / 文本 / 字形 / charset 一律不动。**
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import zx_patch_font                                                 # noqa: E402

if __name__ == '__main__':
    sys.exit(zx_patch_font.main(['--p1', '--report',
                                 os.path.join(zx_patch_font.R82,
                                              'patch_p1_report.json')] + sys.argv[1:]))
