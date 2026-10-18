# -*- coding: utf-8 -*-
r"""timeline.py — 打印若干 EE 地址在全部快照上的**完整取值时间线** (只读)

任务书要的"具体地址 + 变化前后字节 + 时间点"由本工具产出。
"""
import argparse
import glob
import os
import re
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def samples(d, kind='eeram'):
    out = []
    for p in glob.glob(os.path.join(d, 'period_f*_%s.bin' % kind)):
        m = re.search(r'period_f(\d+)_', os.path.basename(p))
        if m:
            out.append((int(m.group(1)), p))
    out.sort()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True)
    ap.add_argument('--addrs', required=True, help='逗号分隔的 VA')
    ap.add_argument('--w', type=int, default=1, help='每个地址打印几个 u32')
    a = ap.parse_args()
    ss = samples(a.dir)
    print('快照 %d 份: %s' % (len(ss), [f for (f, _) in ss]))
    addrs = [int(x, 0) for x in a.addrs.split(',')]
    openers = {}
    for va in addrs:
        for (f, p) in ss:
            fh = open(p, 'rb')
            fh.seek(va)
            b = fh.read(4 * a.w)
            openers.setdefault(va, []).append((f, struct.unpack_from('<%dI' % a.w, b, 0)))
            fh.close()
    hdr = '%-10s' % 'frame' + ''.join('  %-*s' % (a.w * 9, '0x%08X' % va) for va in addrs)
    print(hdr)
    for i in range(len(ss)):
        f = ss[i][0]
        row = '%-10d' % f
        for va in addrs:
            vals = openers[va][i][1]
            cell = ' '.join('%08X' % v for v in vals)
            row += '  %-*s' % (a.w * 9, cell)
        print(row)


if __name__ == '__main__':
    main()
