# -*- coding: utf-8 -*-
r"""r69_wrapfind.py — 在 EE RAM 转储里找"真正折了行的"文本组件。

对每个 vptr ∈ {__vt__6RSHTML, __vt__15RSTextComponent} 的对象, 打印
(W, H, style, 断点数组计数, 断点值, 行长) —— 行数多的就是"visible 介绍框"。

用法: python r69_wrapfind.py <eeram.bin> [--minlines 3]
"""
import argparse
import struct
import sys

VT_RSHTML = 0x005978C0
VT_RSTEXT = 0x005979E0
NAME = {VT_RSHTML: 'RSHTML', VT_RSTEXT: 'RSText'}


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eeram')
    ap.add_argument('--minlines', type=int, default=3)
    a = ap.parse_args()
    d = open(a.eeram, 'rb').read()
    out = []
    for off in range(0, len(d) - 4, 4):
        v = u32(d, off)
        if v not in NAME or off + 0x120 > len(d):
            continue
        w, h = u32(d, off + 0x40), u32(d, off + 0x44)
        arr, cnt = u32(d, off + 0xAC), u32(d, off + 0xB0)
        if not (0 < cnt < 200) or not (0x100000 <= arr < len(d) - 4 * cnt):
            continue
        vals = [u32(d, arr + 4 * i) for i in range(cnt)]
        lines = cnt - 1
        if lines < a.minlines:
            continue
        ln = [vals[i + 1] - vals[i] for i in range(cnt - 1)]
        if any(x < 0 or x > 4000 for x in ln):
            continue
        out.append((lines, off, v, w, h, u32(d, off + 0x1C), vals, ln))
    out.sort(reverse=True)
    print('===== %s : 折了 >= %d 行的组件 %d 个 ====='
          % (a.eeram.split('\\')[-1], a.minlines, len(out)))
    for lines, off, v, w, h, sty, vals, ln in out[:20]:
        print('\n  @%08X %-7s W=%-5d H=%-5d style=%08X  行数=%d'
              % (off, NAME[v], w, h, sty, lines))
        print('     断点 = %s' % vals[:24])
        print('     行长 = %s' % ln[:24])
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
