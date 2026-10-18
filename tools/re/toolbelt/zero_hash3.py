# -*- coding: utf-8 -*-
r"""zero_hash3.py — 那张 4096×u32 表覆盖哪些条目、漏掉哪些（找规律）
"""
import os
import struct
import sys
from collections import Counter

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
SS = 2048


def load(lba):
    base = lba * SS
    hdr = struct.unpack_from('<12I', iso.mm, base)
    cnt = (hdr[3] - 0x830) // 48
    nb = bytes(iso.mm[base + hdr[4]:base + hdr[1]])
    names = [x.decode('latin-1') for x in nb.split(b'\x00') if x]
    tab = struct.unpack_from('<4096I', iso.mm, base + hdr[8])
    return hdr, cnt, names, tab


for nm, lba in (('MENU.IMG', 776286), ('GR.IMG', 19175)):
    hdr, cnt, names, tab = load(lba)
    inb = {v for v in tab if v != 0xFFFFFFFF}
    present = sorted(v for v in inb if v < cnt)
    missing = [i for i in range(cnt) if i not in inb]
    print('=' * 78)
    print('%s 条目 %d ; 表内条目下标 %d ; 漏掉 %d' % (nm, cnt, len(present), len(missing)))
    print('  表内条目下标范围 %d..%d' % (min(present), max(present)))
    print('  表内 前 12 个: %s' % [(i, names[i]) for i in present[:12]])
    print('  漏掉 前 25 个: %s' % [(i, names[i]) for i in missing[:25]])
    # 长度分布
    cl = Counter(len(names[i]) for i in present)
    ml = Counter(len(names[i]) for i in missing)
    print('  表内 名字长度分布: %s' % sorted(cl.items()))
    print('  漏掉 名字长度分布: %s' % sorted(ml.items()))
    # 扩展名分布
    ce = Counter(names[i].rsplit('.', 1)[-1] if '.' in names[i] else '(none)' for i in present)
    me = Counter(names[i].rsplit('.', 1)[-1] if '.' in names[i] else '(none)' for i in missing)
    print('  表内 扩展名 top12: %s' % ce.most_common(12))
    print('  漏掉 扩展名 top12: %s' % me.most_common(12))
    # 漏掉的是否都在名字区后半段?
    print('  表内 最小/最大 下标 %d/%d' % (min(present), max(present)))

iso.close()
