# -*- coding: utf-8 -*-
r"""space_nbr.py -- 逐条目 + gap 打印一个 IMG 的**完整紧凑布局**（只读），并核对 gap 内容归属。"""
import argparse
import hashlib
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib  # noqa: E402

SEC = 2048
LBA = {'menu': 776286, 'gr': 19175}
SIZES = {'menu': 58300882, 'gr': 1550563328}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--target', default='menu', choices=['menu', 'gr'])
    ap.add_argument('--lo', default='0')
    ap.add_argument('--hi', default=None)
    ap.add_argument('--names', default=None, help='逗号分隔: 只列这些名字附近的条目')
    a = ap.parse_args()
    lba, size = LBA[a.target], SIZES[a.target]
    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(9000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)
    live = sorted([e for e in ents if 0 < e['off'] < size and e['stored'] > 0],
                  key=lambda e: e['off'])
    lo = int(a.lo, 16)
    hi = int(a.hi, 16) if a.hi else size
    if a.names:
        # 找这些名字的 off, 取并集区间
        idxs = []
        for nm in a.names.split(','):
            nm = nm.strip()
            for k, e in enumerate(live):
                if e['name'] == nm:
                    idxs.append(k)
        k0, k1 = min(idxs), max(idxs)
        lo = live[max(0, k0 - 1)]['off']
        hi = live[min(len(live) - 1, k1 + 2)]['off'] + live[min(len(live) - 1, k1 + 2)]['stored']
    # 条目内容哈希 (4KB 头)
    hsh = {}
    for e in live:
        if e['stored'] >= 4096:
            hsh.setdefault(hashlib.md5(iso.read(lba * SEC + e['off'], 4096)).hexdigest(),
                           []).append(e['name'])
    print('== %s [0x%X, 0x%X) ==' % (a.target, lo, hi))
    prev_end = None
    for e in live:
        end = e['off'] + e['stored']
        if end <= lo or e['off'] >= hi:
            continue
        if prev_end is not None and e['off'] > prev_end:
            gap = e['off'] - prev_end
            d = iso.read(lba * SEC + prev_end, min(4096, gap))
            z = d.count(0) / len(d) if d else 0
            hh = hashlib.md5(d).hexdigest()
            tag = hsh.get(hh)
            print('   --- GAP 0x%09X len=%-8d zero(4KB)=%.2f %s' %
                  (prev_end, gap, z, ('== %s 的头' % tag) if tag else ''))
        print('   #%-5d %-30s off=0x%09X stored=%-10d real=%-10d end=0x%09X' %
              (e['idx'], e['name'][:30], e['off'], e['stored'], e['real'], end))
        prev_end = end
    if prev_end is not None and prev_end < hi:
        gap = hi - prev_end
        print('   --- TAIL 0x%09X len=%d' % (prev_end, gap))
    iso.close()


main()
