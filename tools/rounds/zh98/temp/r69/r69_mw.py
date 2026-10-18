# -*- coding: utf-8 -*-
r"""r69_mw.py — 解析 -grmemwatch 的 memwatch.bin (本轮 r69: 3 个 RSHTML 实例, 各 288 B, interval 1)。

记录布局 (GRResearch.cpp): 每采样帧, 按 -grmemwatch 给的顺序逐区间写
    [u32 frame][u32 addr][u32 size] + size 字节
⇒ frame_stride = Σ(12 + size_i); 一帧内第 k 个区间的数据在 stride 内偏移 Σ_{j<k}(12+size_j)+12。

用法: python r69_mw.py <memwatch.bin> [--addrs 0x...,0x...] [--field 0x40] [--verbose]
"""
import argparse
import os
import struct
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mw')
    ap.add_argument('--addrs', default='0x0124A6A4,0x0124B650,0x01304E10')
    ap.add_argument('--size', type=int, default=288)
    ap.add_argument('--field', default='0x40,0x44,0x98,0xB4')
    ap.add_argument('--every', type=int, default=600, help='每 N 帧打印一行')
    a = ap.parse_args()
    addrs = [int(x, 16) for x in a.addrs.split(',')]
    fields = [int(x, 16) for x in a.field.split(',')]
    rec = 12 + a.size
    stride = rec * len(addrs)
    sz = os.path.getsize(a.mw)
    nf = sz // stride
    print('memwatch.bin %d B ; 区间 %d 个 x %d B ; 帧记录 stride %d ; 完整帧 %d 张'
          % (sz, len(addrs), a.size, stride, nf))
    print('\n%8s | %s' % ('frame', ' | '.join(
        '@%08X ' % ad + '/'.join('%02X' % f for f in fields) for ad in addrs)))
    last = None
    with open(a.mw, 'rb') as f:
        for k in range(nf):
            f.seek(k * stride)
            buf = f.read(stride)
            if len(buf) < stride:
                break
            fr = struct.unpack_from('<I', buf, 0)[0]
            cells = []
            for i, ad in enumerate(addrs):
                base = i * rec + 12
                got = struct.unpack_from('<I', buf, i * rec + 4)[0]
                vals = []
                for fl in fields:
                    vals.append(struct.unpack_from('<I', buf, base + fl)[0])
                vptr = struct.unpack_from('<I', buf, base)[0]
                cells.append('%08X %s' % (vptr, '/'.join('%08X' % v for v in vals)))
            line = '%8d | %s' % (fr, ' | '.join(cells))
            if k % a.every == 0 or line != last:
                if k % a.every == 0 or last is None:
                    print(line)
            last = line
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
