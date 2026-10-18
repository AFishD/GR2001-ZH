# -*- coding: utf-8 -*-
r"""find_lbn.py — 搜 PS2 盘的 LBA 访问特征（sce_lbn / disc0: / lbn 等）

背景: work/temp/LBA.txt（Elysion 2009）讲透了 Sony isofs 的 LBA 直接访问:
      文件名格式 "%s:/sce_lbn0%x_size0x%x"  ⇒ 特征串 **sce_lbn**
      游戏用它按 LBA 开文件、不沿 ISO 目录下溯 ⇒ 重打包后 LBA 变 ⇒ 访问失效（"LBA 保护"）
      破解法: ① 重生成 LBA 表  ② 改程序（把取 LBA 的操作改成直接用普通文件名）

本脚本: 在 ELF + ISO 全盘里搜特征串与上下文, 判断这游戏用不用 LBA 直接访问。
用法: python find_lbn.py
"""
import io
import os
import re
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r72', 'SLUS_206.13.elf')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
SS = 2048
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 特征串（大小写混合都试）
NEEDLES = [b'sce_lbn', b'sceLbn', b'SCE_LBN', b'lbn0x', b'lbn%', b'size0x',
           b'disc0:', b'cdrom0:', b'cdrom:', b'sceIoOpen', b'sceOpen']
context = 96


def scan(path, label, max_mb=None):
    print('=' * 78)
    print('%s: %s' % (label, path))
    if not os.path.isfile(path):
        print('  ✗ 不存在')
        return
    n = os.path.getsize(path)
    print('  大小 %.1f MB' % (n / 1e6))
    with open(path, 'rb') as f:
        data = f.read()
    total = 0
    for nd in NEEDLES:
        idxs = []
        start = 0
        while True:
            i = data.find(nd, start)
            if i < 0:
                break
            idxs.append(i)
            start = i + 1
            if len(idxs) > 60:
                break
        if idxs:
            total += len(idxs)
            # LBA 位置（ISO 才有意义）
            extra = ''
            if data is not None and path.lower().endswith('.iso'):
                extra = '   LBA≈%d' % (idxs[0] // SS)
            print('  ★ %-10s %d 处  首个偏移 0x%X%s' % (nd.decode('ascii', 'replace'), len(idxs), idxs[0], extra))
            for i in idxs[:3]:
                seg = data[max(0, i - context):i + context]
                txt = ''.join(chr(c) if 32 <= c < 127 else '.' for c in seg)
                print('      @0x%08X  %s' % (i, txt))
        else:
            print('  · %-10s 0 处' % nd.decode('ascii', 'replace'))
    print('  合计命中 %d' % total)


scan(ELF, 'ELF (SLUS_206.13, 主程序)')
scan(ISO, 'ISO (GR_ZH113b 整盘)')
