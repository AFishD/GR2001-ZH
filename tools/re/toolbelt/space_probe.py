# -*- coding: utf-8 -*-
r"""space_probe.py -- 对某个 IMG 偏移区间做取证（只读）：邻域条目、内容结构、熵。"""
import argparse
import json
import math
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
LBA = {'menu': 776286, 'gr': 19175}


def entropy(b):
    c = Counter(b)
    n = len(b)
    return -sum((v / n) * math.log2(v / n) for v in c.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH113b',
                                                  'GR_ZH113b.iso'))
    ap.add_argument('--target', default='gr', choices=['gr', 'menu'])
    ap.add_argument('--off', required=True, help='IMG 相对偏移 (hex)')
    ap.add_argument('--len', type=int, default=4096)
    ap.add_argument('--ctx', type=int, default=6, help='前后各列几个条目')
    a = ap.parse_args()
    off = int(a.off, 16)
    lba = LBA[a.target]
    iso = tcslib.Iso(a.iso)
    ents = []
    for i in range(9000):
        e = iso.img_entry(lba, i)
        nm = e['name']
        if nm.startswith('?') and e['off'] == 0 and e['stored'] == 0:
            break
        e['idx'] = i
        ents.append(e)
    live = sorted([e for e in ents if e['off'] > 0], key=lambda e: e['off'])
    print('== %s off=0x%X 邻域 ==' % (a.target, off))
    k = 0
    for j, e in enumerate(live):
        if e['off'] + e['stored'] <= off:
            k = j
        else:
            break
    for j in range(max(0, k - a.ctx), min(len(live), k + 2 + a.ctx)):
        e = live[j]
        mark = '  <-- 前一' if j == k else ('  <-- 后一' if j == k + 1 else '')
        print('   #%-5d %-30s off=0x%09X stored=%-10d real=%-10d end=0x%09X gap=%+d%s'
              % (e['idx'], e['name'][:30], e['off'], e['stored'], e['real'],
                 e['off'] + e['stored'], off - (e['off'] + e['stored']), mark))
    # 内容
    d = iso.read((lba * SEC) + off, a.len)
    print('\n  first 128 B hex: %s' % d[:128].hex())
    print('  first 128 B asc: %s' % ''.join(chr(c) if 32 <= c < 127 else '.' for c in d[:128]))
    print('  entropy(4KB)=%.3f  zero=%.3f' %
          (entropy(d), d.count(0) / len(d)))
    # 分块零率
    print('  逐 4KB 零率: %s' % ' '.join(
        '%.2f' % (iso.read((lba * SEC) + off + i * 4096, 4096).count(0) / 4096.0)
        for i in range(0, min(16, a.len // 4096))))
    # 4 字节结构扫描: 像不像条目表/指针
    arr = np.frombuffer(d, dtype='<u4')
    print('  u32 统计: <0x1000=%d  <IMG大小=%d  ==0xFFFFFFFF=%d  ==0=%d  总=%d'
          % (int((arr < 0x1000).sum()), int((arr < 0x5C6BB800).sum()),
             int((arr == 0xFFFFFFFF).sum()), int((arr == 0).sum()), arr.size))
    iso.close()


main()
