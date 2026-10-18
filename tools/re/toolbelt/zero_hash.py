# -*- coding: utf-8 -*-
r"""zero_hash.py — 解析 IMG 头 +0x20 指向的 16,384 B 结构（疑似条目哈希/索引表）

MENU.IMG: 头 u32[+0x20] = 0x9230, 结构占 [0x9230, 0xD230) = 0x4000
GR.IMG  : 头 u32[+0x20] = 0x30CB0, 结构占 [0x30CB0, 0x34CB0) = 0x4000
两容器**同样大小** ⇒ 很可能是定长哈希表。必须搞清它，否则加条目后名字查不到。
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
LS = []


def say(s=''):
    print(s)
    LS.append(s)


def entries(base):
    tbl_end = struct.unpack_from('<I', iso.mm, base + 0x0C)[0]
    names_start = struct.unpack_from('<I', iso.mm, base + 0x10)[0]
    names_end = struct.unpack_from('<I', iso.mm, base + 0x04)[0]
    cnt = (tbl_end - 0x830) // 48
    names = [x.decode('latin-1') for x in
             bytes(iso.mm[base + names_start:base + names_end]).split(b'\x00') if x]
    return cnt, names, tbl_end, names_start


for nm, lba, size in (('MENU.IMG', 776286, 58300882), ('GR.IMG', 19175, 1550563328)):
    base = lba * 2048
    hdr = struct.unpack_from('<12I', iso.mm, base)
    say('=' * 78)
    say('%s  头 12 个 u32: %s' % (nm, ' '.join('0x%X' % v for v in hdr)))
    cnt, names, tbl_end, names_start = entries(base)
    p = hdr[8]
    say('  条目 %d ; u32[+0x20]=0x%X ; 名字区 [0x%X,0x%X)' % (cnt, p, names_start, hdr[1]))
    if not (0 < p < names_start):
        say('  u32[+0x20] 不在空隙内 —— 假设不成立，停止')
        continue
    blob = iso.read(base + p, names_start - p)
    say('  结构 [0x%X,0x%X) = %d B' % (p, names_start, len(blob)))
    # 前 64 字节
    for k in range(0, min(64, len(blob)), 16):
        say('    +0x%04X  %s' % (k, blob[k:k + 16].hex(' ')))
    u32 = struct.unpack_from('<%dI' % (len(blob) // 4), blob, 0)
    nz = [i for i, v in enumerate(u32) if v != 0xFFFFFFFF]
    say('  u32 槽 %d 个 ; 非 0xFFFFFFFF 槽 %d 个' % (len(u32), len(nz)))
    from collections import Counter
    c = Counter(u32[i] for i in nz)
    say('  非空槽取值分布 top20: %s' % c.most_common(20))
    say('  槽 0..15: %s' % ['0x%X' % v for v in u32[:16]])
    say('  非空槽下标前 24: %s' % nz[:24])
    # 试试是不是 u16 表
    u16 = struct.unpack_from('<%dH' % (len(blob) // 2), blob, 0)
    n16 = [i for i, v in enumerate(u16) if v != 0xFFFF]
    c16 = Counter(u16[i] for i in n16)
    say('  按 u16 看: 槽 %d, 非 0xFFFF %d, top20 %s' % (len(u16), len(n16), c16.most_common(20)))

iso.close()
open(os.path.join(OUT, 'img_hash.txt'), 'w', encoding='utf-8').write('\n'.join(LS) + '\n')
print('\n[OUT] %s' % os.path.join(OUT, 'img_hash.txt'))
