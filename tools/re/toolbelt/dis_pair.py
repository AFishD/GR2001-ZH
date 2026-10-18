# -*- coding: utf-8 -*-
r"""dis_pair.py — 把"原版 ELF"与"汉化 ELF"某一段逐指令并排打印, 找"改了 u16 但漏改配套偏移"的地方

用法: python dis_pair.py <起始VA> <结束VA>
默认打 0x219B60..0x219D80 (DrawString/解码器路径) 与 0x21A3A0..0x21A480 (ReallocateSize 一带)
"""
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'rounds', 'zh98', 'temp', 'r74'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

try:
    from r74_mips import dis as mips_dis  # 自带 R5900+MMI 解码器
except Exception as e:
    print('✗ 无法导入 r74_mips: %s' % e)
    sys.exit(1)

SEG_VA, SEG_OFF = 0x100000, 0x80


def va2off(va):
    return SEG_OFF + (va - SEG_VA)


def elf(iso):
    return tcslib.Iso(iso).read(295 * 2048, 38057892 - 604160)


orig = elf(os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
mod = elf(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))

RANGES = [(0x219B60, 0x219D80, 'DrawString / 解码器路径'),
          (0x21A3A0, 0x21A480, 'RSFontMgr::ReallocateSize 一带'),
          (0x21AC60, 0x21AD40, 'StringWidth/CharWidth 一带')]
if len(sys.argv) >= 3:
    RANGES = [(int(sys.argv[1], 0), int(sys.argv[2], 0), '用户指定')]

for a, b, label in RANGES:
    print('=' * 100)
    print('%s   0x%08X..0x%08X' % (label, a, b))
    print('=' * 100)
    o, m = va2off(a), va2off(b)
    for va in range(a, b, 4):
        k = va2off(va)
        wo = int.from_bytes(orig[k:k + 4], 'little')
        wm = int.from_bytes(mod[k:k + 4], 'little')
        mark = '   ' if wo == wm else ' ★ '
        try:
            do = mips_dis(wo, va)
        except Exception:
            do = '%08X  ?' % wo
        try:
            dm = mips_dis(wm, va)
        except Exception:
            dm = '%08X  ?' % wm
        if wo == wm:
            print('  %s 原=汉 0x%08X  %s' % (mark, va, do))
        else:
            print('  %s 0x%08X' % (mark, va))
            print('         原: %s' % do)
            print('         汉: %s' % dm)
    print()
