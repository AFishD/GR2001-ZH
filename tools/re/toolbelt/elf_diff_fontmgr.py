# -*- coding: utf-8 -*-
r"""elf_diff_fontmgr.py — 原版 vs 汉化 ELF 在 RSFontMgr 区段的逐指令对照

为什么: 反编译发现 RSFontMgr::ReallocateSize(@0x21A3B0) 与 AddOneWord(@0x219F50) —
        "按字符数申请缓冲、按字节数写"最可能就在这里。先看汉化到底改没改这一段。

原版 ELF 来自 GR_EN_ORIG（CRC 3E571E95），汉化来自 GR_ZH111/113b（CRC 7A361FB5）。
ELF 映射: 文件偏移 = 0x80 + (VA - 0x100000)。两个 ELF 均从 ISO LBA295 读 37,453,732 B。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

SEG_VA, SEG_OFF = 0x100000, 0x80
RANGES = [
    (0x219380, 0x21A600, 'RSFontMgr 全区 (ReadResourceFile/Create/ReallocateSize/AddOneWord/Flush/Draw)'),
    (0x21AB50, 0x21B000, 'CharWidth/StringWidth/CharHeight 一带'),
    (0x21ADE0, 0x21AF00, 'ComputeCharTextureCoords'),
    (0x219A70, 0x219F60, 'DrawString 系'),
    (0x416ED0, 0x417200, '汉化 cave (解码器 / 宽度 / 网格)'),
]


def get_elf(iso_path):
    iso = tcslib.Iso(iso_path)
    return iso.read(295 * 2048, 38057892 - 604160)


def va2off(va):
    return SEG_OFF + (va - SEG_VA)


orig = get_elf(os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
mod = get_elf(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
print('原版 ELF %d B ; 汉化 ELF %d B' % (len(orig), len(mod)))
print()

total_diff = 0
for a, b, label in RANGES:
    o, m = va2off(a), va2off(b)
    n = (b - a) // 4
    words_o = struct.unpack_from('<%dI' % n, orig, o)
    words_m = struct.unpack_from('<%dI' % n, mod, o)
    diffs = [i for i in range(n) if words_o[i] != words_m[i]]
    total_diff += len(diffs)
    print('=== 0x%06X..0x%06X  %s ===' % (a, b, label))
    print('    %d 个 4 字节字中, **%d 个不同**' % (n, len(diffs)))
    for i in diffs[:14]:
        va = a + i * 4
        print('      0x%08X  原 %08X  →  汉 %08X' % (va, words_o[i], words_m[i]))
    if len(diffs) > 14:
        print('      … 还有 %d 个' % (len(diffs) - 14))
    print()

print('五个区段合计不同 %d 个字' % total_diff)

# 全 ELF 差异区间概览（确认汉化只在自己的区域动手）
print()
print('=== 全 ELF 差异区间概览（相邻差异合并成段）===')
n = min(len(orig), len(mod)) // 4
wo = struct.unpack_from('<%dI' % n, orig, SEG_OFF)
wm = struct.unpack_from('<%dI' % n, mod, SEG_OFF)
segs = []
cur = None
for i in range(n):
    if wo[i] != wm[i]:
        va = SEG_VA + i * 4
        if cur and va - cur[1] <= 8:
            cur[1] = va
            cur[2] += 1
        else:
            if cur:
                segs.append(cur)
            cur = [va, va, 1]
if cur:
    segs.append(cur)
print('  共 %d 段' % len(segs))
for a, b, c in segs[:40]:
    print('    0x%08X..0x%08X  (%d 字)' % (a, b, c))
if len(segs) > 40:
    print('    … 还有 %d 段' % (len(segs) - 40))
