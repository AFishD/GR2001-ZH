# -*- coding: utf-8 -*-
r"""space_region.py -- 把一个偏移区间按块画像 + 找其中的"文件起点"（只读）。"""
import argparse
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
LBA = {'menu': 776286, 'gr': 19175}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--target', default='gr', choices=['gr', 'menu'])
    ap.add_argument('--off', required=True)
    ap.add_argument('--len', type=int, required=True)
    ap.add_argument('--blk', type=int, default=65536)
    ap.add_argument('--find', default=None,
                    help='在该区间里找某条目名开头 64B（逗号分隔多个名字）')
    a = ap.parse_args()
    off = int(a.off, 16)
    lba = LBA[a.target]
    iso = tcslib.Iso(a.iso)
    d = iso.read(lba * SEC + off, a.len)
    print('== %s [0x%X, 0x%X) len=%d ==' % (a.target, off, off + a.len, a.len))
    for i in range(0, a.len, a.blk):
        b = d[i:i + a.blk]
        arr = np.frombuffer(b, dtype=np.uint8)
        z = float((arr == 0).sum()) / len(b)
        pr = float(((arr >= 32) & (arr < 127)).sum()) / len(b)
        head = b[:48]
        asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in head)
        print('  +0x%08X z=%.3f pr=%.3f | %s' % (i, z, pr, asc))
    if a.find:
        ents = {}
        for i in range(9000):
            e = iso.img_entry(lba, i)
            nm = e['name']
            if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
                break
            ents[nm] = e
        for nm in a.find.split(','):
            nm = nm.strip()
            if nm not in ents:
                print('  [%s] 条目不存' % nm)
                continue
            e = ents[nm]
            n = min(e['stored'], 65536)
            needle = iso.read(lba * SEC + e['off'], n)
            p = d.find(needle)
            print('  [%s] idx=%d off=0x%X stored=%d -> 在区间内 %s'
                  % (nm, e['idx'], e['off'], e['stored'],
                     ('命中 @ +0x%X' % p) if p >= 0 else '无'))
    iso.close()


main()
