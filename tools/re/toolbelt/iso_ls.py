# -*- coding: utf-8 -*-
r"""iso_ls.py — 列出 ISO 里某个目录的内容（以及全盘文件树一层）

用法: python iso_ls.py [<iso>] [<目录LBA> <目录长度>]
不带参数时: 打印根目录 + MODULES 子目录
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ISO = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
SS = 2048
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
f = open(ISO, 'rb')


def ls(lba, length, title):
    f.seek(lba * SS)
    d = f.read(length)
    print('=== %s (LBA %d, %d B) ===' % (title, lba, length))
    out = []
    i = 0
    while i < len(d):
        L = d[i]
        if L == 0:
            i += 1
            continue
        rec = d[i:i + L]
        e_lba = struct.unpack_from('<I', rec, 2)[0]
        e_len = struct.unpack_from('<I', rec, 10)[0]
        flags = rec[25]
        nl = rec[32]
        name = rec[33:33 + nl].decode('ascii', 'replace')
        out.append((name, e_lba, e_len, flags))
        i += L
    for name, e_lba, e_len, flags in out:
        kind = '[目录]' if flags & 2 else '      '
        print('  %-26s %s LBA %-8d 大小 %-12d' % (name, kind, e_lba, e_len))
    print()
    return out


# 根目录
root = ls(261, 384, '根目录')
# 找 MODULES 子目录并展开
for name, lba, ln, flags in root:
    n = name.rstrip(';1').upper()
    if n == 'MODULES' and (flags & 2):
        sub = ls(lba, ln, 'MODULES 子目录')
        # 展开其中所有子目录
        for sn, slba, sln, sfl in sub:
            if (sfl & 2) and sn not in ('.', '..'):
                ls(slba, sln, 'MODULES\\%s' % sn)
