# -*- coding: utf-8 -*-
r"""zero_imgmap.py — 检查 IMG 容器「表尾..名字区」之间那 18,784 B 空隙里到底是什么（只读）

img_add_entry.py 的配方会把名字区整体前移到「新表尾」，也就是**写进这块空隙**。
所以必须先看清空隙里有没有活数据（路径表？索引？），否则加条目会踩坏它。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
SS = 2048
LS = []


def say(s=''):
    print(s)
    LS.append(s)


for nm, lba, size in (('MENU.IMG', 776286, 58300882), ('GR.IMG', 19175, 1550563328)):
    base = lba * SS
    h = struct.unpack_from('<5I', iso.mm, base)
    tbl_end, names_start = h[3], h[4]
    say('=' * 78)
    say('%s @0x%X  头 = size=%d names_end=%d sector=%d tbl_end=0x%X names_start=0x%X'
        % (nm, base, h[0], h[1], h[2], h[3], h[4]))
    gap = iso.read(base + tbl_end, names_start - tbl_end)
    say('  空隙 [0x%X,0x%X) = %d B' % (tbl_end, names_start, len(gap)))
    nz = sum(1 for b in gap if b)
    say('  非零字节 %d / %d' % (nz, len(gap)))
    # 统计非零段
    segs = []
    i = 0
    while i < len(gap):
        if gap[i]:
            j = i
            while j < len(gap) and (gap[j] or (j + 1 < len(gap) and gap[j + 1])):
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    say('  非零段 %d 个 (前 20):' % len(segs))
    for a, b in segs[:20]:
        raw = gap[a:b]
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in raw)
        say('    +0x%-6X len=%-6d %s | %s' % (a, b - a, raw[:32].hex(' '), asc[:64]))
    # 头部的 0x830 之前是什么
    pre = iso.read(base, 0x830)
    say('  头+[0,0x830) 非零段:')
    i = 0
    while i < len(pre):
        if pre[i]:
            j = i
            while j < len(pre) and pre[j]:
                j += 1
            raw = pre[i:j]
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in raw)
            say('    @0x%-6X len=%-5d %s | %s' % (i, j - i, raw[:24].hex(' '), asc[:60]))
            i = j
        else:
            i += 1
    # 名字区尾部到数据区起点
    first_off = min(struct.unpack_from('<I', iso.mm, base + 0x830 + 48 * k + 32)[0]
                    for k in range((tbl_end - 0x830) // 48))
    tailzone = iso.read(base + h[1], first_off - h[1])
    say('  名字区末[0x%X]..数据区首[0x%X) = %d B ; 非零 %d'
        % (h[1], first_off, len(tailzone), sum(1 for b in tailzone if b)))

open(os.path.join(OUT, 'img_gap.txt'), 'w', encoding='utf-8').write('\n'.join(LS) + '\n')
print('\n[OUT] %s' % os.path.join(OUT, 'img_gap.txt'))
iso.close()
