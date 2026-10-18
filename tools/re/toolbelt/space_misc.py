# -*- coding: utf-8 -*-
r"""space_misc.py -- 收尾取证（只读）：
  * MENU.IMG / GR.IMG 的"非零孤儿 gap"到底是什么（与谁相似 / 内部结构）
  * COMMON.PAK 的 arrow 记录（PSMCT32）颜色数 ⇒ 能否位深回收
  * MODULES / SYSTEM.CNF / IOPRP242 只读评估
"""
import json
import os
import struct
import sys
from collections import Counter

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
MENU_LBA, GR_LBA = 776286, 19175


def main():
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))

    # ---------- 1) 孤儿 gap 的身份 ----------
    print('=== 1) 大块非零孤儿 gap ===')
    cases = [('menu', 0x20D0EC, 47636), ('menu', 0x36B0D9C, 49540),
             ('gr', 0x5C012815, 159451), ('gr', 0x5C039A69, 53255),
             ('gr', 0x5C04EE5F, 51905), ('gr', 0x5C083C0B, 52213)]
    lba = {'menu': MENU_LBA, 'gr': GR_LBA}
    for tag, off, ln in cases:
        d = iso.read(lba[tag] * SEC + off, min(ln, 1 << 20))
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in d[:64])
        pr = sum(1 for c in d if 32 <= c < 127) / len(d)
        z = d.count(0) / len(d)
        # 有没有 LZO 帧头 {plen}{osz}
        frames = 0
        p = 0
        while p + 8 <= len(d) and frames < 4:
            L, S = struct.unpack_from('<II', d, p)
            if 0 < L <= len(d) - p - 8 and 0 < S < 8 << 20 and L < S:
                frames += 1
                p += 8 + L
            else:
                break
        print('  %s 0x%09X len=%-8d z=%.3f pr=%.3f lzoframes=%d' % (tag, off, ln, z, pr, frames))
        print('       head: %s' % asc)

    # ---------- 2) arrow 记录颜色数 ----------
    print('\n=== 2) COMMON.PAK arrow (psm=0 PSMC32) 能否位深回收 ===')
    for tag, lb in (('MENU', MENU_LBA), ('GR', GR_LBA)):
        for i in range(6000):
            e = iso.img_entry(lb, i)
            if e['name'] == 'COMMON.PAK':
                pak = iso.read(e['iso_off'], e['stored'])
                break
        # arrow record: hdr_off 0, px_off 0x21, px 0x1010
        blob = pak[0x21:0x21 + 0x1010]
        arr = np.frombuffer(blob[:0x1000], dtype='<u4')
        uniq = np.unique(arr)
        print('  %s arrow: %d 像素, 唯一 u32 = %d, 头 8 = %s' %
              (tag, arr.size, uniq.size, [hex(int(x)) for x in uniq[:8]]))
        # 也看 16 位压缩后唯一数
        lo16 = (arr & 0xFFFF).astype(np.uint32)
        print('       低16位唯一 = %d ; 高16位唯一 = %d' %
              (np.unique(lo16).size, np.unique((arr >> 16)).size))
    iso.close()

    # ---------- 3) MODULES / SYSTEM.CNF 只读评估 ----------
    print('\n=== 3) 非 IMG 区只读评估 ===')
    import subprocess
    print('  (由 tools/iso_build/iso_tools.py 或手工 lba 表给出; 见报告)')
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
    cnf = iso.read(294 * SEC, 57)
    print('  SYSTEM.CNF(57B @LBA294) = %r' % cnf)
    mods = iso.read(262 * SEC, 1344)
    # 目录记录
    p = 0
    names = []
    while p < len(mods):
        L = mods[p]
        if L == 0:
            p += 1
            continue
        rec = mods[p:p + L]
        if len(rec) < 33:
            break
        nlen = rec[32]
        nm = rec[33:33 + nlen].decode('latin-1')
        ext = struct.unpack_from('<I', rec, 10)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        szle = struct.unpack_from('<I', rec, 10)[0]
        lba_ = struct.unpack_from('<I', rec, 2)[0]
        size_ = struct.unpack_from('<I', rec, 10)[0]
        if nm not in ('\x00', '\x01'):
            names.append((nm, lba_, size_))
        p += L
    print('  MODULES/ 目录 (%d B) 解析出 %d 条:' % (len(mods), len(names)))
    tot = 0
    for nm, lba_, size_ in names:
        if size_ and lba_:
            tot += size_
            print('     %-20s LBA=%-7d size=%-9d' % (nm, lba_, size_))
    print('  模块合计 %d B' % tot)
    # IOPRP242.IMG 头
    for nm, lba_, size_ in names:
        if 'IOPRP' in nm:
            d = iso.read(lba_ * SEC, 64)
            print('  %s 头: %s' % (nm, d[:32].hex()))
    iso.close()


main()
