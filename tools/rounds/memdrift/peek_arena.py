# -*- coding: utf-8 -*-
r"""peek_arena.py — 把 EE RAM 快照里某个地址的字节按时间序列打出来 (只读)

用途: 核实 VA 0x0055B7A0 (= 反汇编里 `lui $v0,0x56; addiu $v0,$v0,-18528`,
即 dlmalloc 的 malloc_state 全局) 在汉化盘上是否随时间漂移/被清零。
"""
import glob
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
EE = 32 * 1024 * 1024


def samples(d, kind='eeram'):
    out = []
    for p in glob.glob(os.path.join(d, 'period_f*_%s.bin' % kind)):
        m = re.search(r'period_f(\d+)_', os.path.basename(p))
        if m:
            out.append((int(m.group(1)), p))
    out.sort()
    return out


def show(d, va, n=64, nwords=8):
    ss = samples(d)
    if not ss:
        print('  (%s 里没有 period_*_eeram.bin)' % d)
        return
    print('=== %s : VA 0x%08X 起 %d 字节 ===' % (os.path.basename(d), va, n))
    print('  %-8s %s' % ('frame', ' '.join('%08X' % (va + 4 * i) for i in range(nwords))))
    prev = None
    for (f, p) in ss:
        with open(p, 'rb') as fh:
            fh.seek(va)
            b = fh.read(n)
        ws = [struct.unpack_from('<I', b, 4 * i)[0] for i in range(nwords)]
        mark = ''
        if prev is not None and ws != prev:
            mark = '   <-- 变化'
        print('  %-8d %s%s' % (f, ' '.join('%08X' % x for x in ws), mark))
        prev = ws


if __name__ == '__main__':
    d = sys.argv[1]
    vas = [int(x, 0) for x in sys.argv[2:]] or [0x0055B7A0]
    for va in vas:
        show(d, va)
        print()
