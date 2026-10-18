# -*- coding: utf-8 -*-
r"""r69_at.py — 打印转储里若干地址处的对象首 0x120 字节 (按字段解读)。

用法: python r69_at.py <eeram.bin> <hexaddr> [hexaddr...]
"""
import struct
import sys

NAMES = {0x00: 'vptr', 0x1C: 'style', 0x3C: 'top?', 0x40: 'W', 0x44: 'H', 0x48: 'cx?',
         0x4C: '4C', 0x98: 'font', 0x9C: '9C', 0xAC: 'brkArr', 0xB0: 'B0', 0xB4: 'B4(u8)',
         0xD8: 'D8', 0xDC: 'DC', 0xEC: 'y', 0xF0: 'F0', 0xF4: 'f4', 0xF8: 'f8', 0xFC: 'scroll',
         0x108: '108', 0x110: '110', 0x114: '114'}


def main():
    d = open(sys.argv[1], 'rb').read()
    for a in sys.argv[2:]:
        off = int(a, 16)
        print('===== @%08X =====' % off)
        for k in sorted(NAMES):
            v = struct.unpack_from('<I', d, off + k)[0]
            print('   +0x%03X %-8s = %08X  (%d)' % (k, NAMES[k], v, v))
        print('   hexdump +0x00..0x40: %s' % d[off:off + 0x40].hex(' '))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
