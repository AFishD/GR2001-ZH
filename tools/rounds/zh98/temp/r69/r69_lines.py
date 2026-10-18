# -*- coding: utf-8 -*-
r"""r69_lines.py — 列出转储里"行数组"(comp[0x110]/[0x114])非空的文本组件。

`RSHTML::CreateStrings` 把折行结果按行 Substring 进 comp+0x110 的 RSArray<RSUIString>,
元素 8 字节、计数在 comp+0x114 ⇒ 计数 = 该组件当前渲染的**行数**。

用法: python r69_lines.py <eeram.bin> [<eeram2.bin> ...] [--min 8]
"""
import argparse
import struct
import sys

VT = {0x005978C0: 'RSHTML', 0x005979E0: 'RSText'}
NAME = VT


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def rows(d):
    out = {}
    for off in range(0, len(d) - 4, 4):
        v = u32(d, off)
        if v not in NAME or off + 0x120 > len(d):
            continue
        cnt = u32(d, off + 0x114)
        ptr = u32(d, off + 0x110)
        if not (0x100000 <= ptr < len(d) - 8) or not (0 < cnt < 5000):
            continue
        out[off] = (NAME[v], u32(d, off + 0x40), u32(d, off + 0x44),
                    u32(d, off + 0x1C), cnt, u32(d, off + 0x3C), u32(d, off + 0x9C),
                    u32(d, off + 0xF8), d[off + 0xB4])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('eeram', nargs='+')
    ap.add_argument('--min', type=int, default=8)
    a = ap.parse_args()
    res = {}
    for p in a.eeram:
        res[p] = rows(open(p, 'rb').read())
    for p, r in res.items():
        big = {k: v for k, v in r.items() if v[4] >= a.min}
        print('===== %s : 行数 >= %d 的组件 %d 个 ====='
              % (p.split('\\')[-1], a.min, len(big)))
        for off in sorted(big):
            v = big[off]
            print('   @%08X %-7s W=%-5d H=%-5d style=%08X 行数=%-5d ay=%-5d 9C=%-3d f8=%-4d B4=%d'
                  % (off, v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8]))
        print()
    if len(res) == 2:
        (p1, r1), (p2, r2) = list(res.items())
        print('===== 两份转储的逐组件差异 (只看行数>=%d 的) =====' % a.min)
        keys = sorted(set(k for k, v in r1.items() if v[4] >= a.min) |
                      set(k for k, v in r2.items() if v[4] >= a.min))
        for k in keys:
            v1, v2 = r1.get(k), r2.get(k)
            if v1 == v2:
                print('   @%08X 完全相同  %s' % (k, v1))
            else:
                print('   @%08X ★不同\n        A=%s\n        B=%s' % (k, v1, v2))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
