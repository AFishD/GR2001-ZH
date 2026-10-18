# -*- coding: utf-8 -*-
r"""r69_brk.py — 读 RSHTML/RSTextComponent 的断点数组 (comp[0xAC], 计数 comp[0xB0])。

用法: python r69_brk.py <eeram.bin> <compaddr_hex> [...]
"""
import struct
import sys


def u32(d, off):
    return struct.unpack_from('<I', d, off)[0]


def main():
    d = open(sys.argv[1], 'rb').read()
    for a in sys.argv[2:]:
        off = int(a, 16)
        arr = u32(d, off + 0xAC)
        cnt = u32(d, off + 0xB0)
        print('===== comp @%08X : 断点数组 %08X 计数 %d =====' % (off, arr, cnt))
        if not (0 < cnt < 64) or not (0x100000 <= arr < len(d) - 4 * cnt):
            print('   (计数/指针不合理, 跳过)')
            continue
        vals = [u32(d, arr + 4 * i) for i in range(cnt)]
        print('   值 = %s' % vals)
        print('   行长 = %s' % [vals[i + 1] - vals[i] for i in range(cnt - 1)])
        # 字符串数组 comp[0x110]
        sv = u32(d, off + 0x110)
        sn = u32(d, off + 0x114)
        print('   comp[0x110]=%08X comp[0x114]=%d' % (sv, sn))
        if 0x100000 <= sv < len(d) - 8 and 0 < sn < 400:
            for i in range(min(sn, 400)):
                p = u32(d, sv + 4 * i)
                if not (0x100000 <= p < len(d) - 0x80):
                    print('      [%3d] 指针 %08X 不合理' % (i, p))
                    break
                # RSUIString: 先看前 8 字节
                print('      [%3d] obj=%08X  head=%s' % (i, p, d[p:p + 16].hex(' ')))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
