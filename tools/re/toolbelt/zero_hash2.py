# -*- coding: utf-8 -*-
r"""zero_hash2.py — 判定 IMG 头 +0x20 那张 4096×u32 表到底是什么

测试假设:
  H1: slot = hash(name) mod 4096,  value = 条目下标 (开放寻址/线性探测)
  H2: slot = 条目下标 的某种重排, value = 名字区偏移
  H3: slot = 名字区偏移 (u32[+0x2c]? )
"""
import os
import struct
import sys
import zlib
from collections import Counter

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)


def load(lba, size):
    base = lba * 2048
    hdr = struct.unpack_from('<12I', iso.mm, base)
    tbl_end, names_start, names_end = hdr[3], hdr[4], hdr[1]
    cnt = (tbl_end - 0x830) // 48
    ents = [struct.unpack_from('<12I', iso.mm, base + 0x830 + 48 * i) for i in range(cnt)]
    nb = bytes(iso.mm[base + names_start:base + names_end])
    names = [x.decode('latin-1') for x in nb.split(b'\x00') if x]
    # 每条名字在名字区里的偏移
    noffs, p = [], 0
    for x in nb.split(b'\x00'):
        if x:
            noffs.append(p)
        p += len(x) + 1
    tab = struct.unpack_from('<4096I', iso.mm, base + hdr[8])
    return dict(base=base, hdr=hdr, cnt=cnt, ents=ents, names=names, noffs=noffs, tab=tab,
                nb=nb)


def hashes(s):
    b = s.encode('latin-1')
    out = {}
    h = 0
    for c in b:
        h = (h * 33 + c) & 0xFFFFFFFF
    out['djb2_0'] = h
    h = 5381
    for c in b:
        h = (h * 33 + c) & 0xFFFFFFFF
    out['djb2'] = h
    h = 0
    for c in b:
        h = (c + (h << 6) + (h << 16) - h) & 0xFFFFFFFF
    out['sdbm'] = h
    h = 2166136261
    for c in b:
        h ^= c
        h = (h * 16777619) & 0xFFFFFFFF
    out['fnv1a'] = h
    h = 0
    for c in b:
        h = (h + c) & 0xFFFFFFFF
    out['sum'] = h
    out['crc32'] = zlib.crc32(b) & 0xFFFFFFFF
    out['lower_djb2'] = None
    h = 5381
    for c in s.lower().encode('latin-1'):
        h = (h * 33 + c) & 0xFFFFFFFF
    out['lower_djb2'] = h
    h = 0
    for c in s.upper().encode('latin-1'):
        h = (h * 33 + c) & 0xFFFFFFFF
    out['upper_djb2_0'] = h
    return out


for nm, lba, size in (('MENU.IMG', 776286, 58300882), ('GR.IMG', 19175, 1550563328)):
    d = load(lba, size)
    tab = d['tab']
    nz = [i for i, v in enumerate(tab) if v != 0xFFFFFFFF]
    vals = [tab[i] for i in nz]
    print('=' * 78)
    print('%s  条目 %d ; 表非空槽 %d ; value min=%d max=%d ; value<条目数 的个数=%d'
          % (nm, d['cnt'], len(nz), min(vals), max(vals),
             sum(1 for v in vals if v < d['cnt'])))
    print('  value 去重后 %d 个 ; 是否覆盖全部条目下标? %s'
          % (len(set(vals)), set(range(d['cnt'])) <= set(vals)))
    # H1: 每个名字算 hash, 看 slot 是否非空
    for hn in ('djb2', 'djb2_0', 'sdbm', 'fnv1a', 'sum', 'crc32', 'lower_djb2', 'upper_djb2_0'):
        hit = 0
        for s in d['names']:
            h = hashes(s)[hn]
            if h is not None and tab[h & 0xFFF] != 0xFFFFFFFF:
                hit += 1
        print('  H1 %-12s slot=hash&0xFFF 命中非空槽: %d / %d' % (hn, hit, len(d['names'])))
    # H2: 表值是否是名字区偏移
    offs = set(d['noffs'])
    print('  H2 value ∈ 名字区偏移集合? %d / %d'
          % (sum(1 for v in vals if v in offs), len(vals)))
    # H3: 表值是否是条目表字段
    f6 = {e[6] for e in d['ents']}
    f7 = {e[7] for e in d['ents']}
    f8 = {e[8] for e in d['ents']}
    print('  H3 value ∈ {stored}: %d ; ∈{real}: %d ; ∈{off}: %d'
          % (sum(1 for v in vals if v in f6), sum(1 for v in vals if v in f7),
             sum(1 for v in vals if v in f8)))
    # 打印前 30 个非空槽 + 对应条目名(若 value 是下标)
    print('  前 30 非空槽 [slot]=value -> name[value]')
    for i in nz[:30]:
        v = tab[i]
        nme = d['names'][v] if v < len(d['names']) else '?'
        print('     [%4d] = %-6d  %r' % (i, v, nme))

iso.close()
