# -*- coding: utf-8 -*-
r"""r69_comp.py — 在 EE RAM 转储里枚举文本组件对象 (vptr 精确签名)。

vptr = __vt__6RSHTML          @ 0x005978C0   (RSHTML 自身, 即"介绍框"这一族)
       __vt__15RSTextComponent @ 0x005979E0

用法: python r69_comp.py <eeram.bin> [...] [--vptr HEX,HEX] [--wmin N] [--max N]
"""
import os
import struct
import sys

VTS = [0x005978C0, 0x005979E0]
VTNAME = {0x005978C0: 'RSHTML', 0x005979E0: 'RSTextComponent'}
VTLO, VTHI = 0x00580000, 0x005C0000


def u32(d, off):
    return struct.unpack_from('<I', d, off)[0]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    vts = list(VTS)
    limit = 60
    for i, a in enumerate(sys.argv):
        if a == '--vptr':
            vts = [int(x, 16) for x in sys.argv[i + 1].split(',')]
        if a == '--max':
            limit = int(sys.argv[i + 1])
    for path in args:
        d = open(path, 'rb').read()
        hits = {v: [] for v in vts}
        for off in range(0, len(d) - 4, 4):
            v = u32(d, off)
            if v in hits:
                hits[v].append(off)
        print('===== %s (%d B) =====' % (os.path.basename(path), len(d)))
        for vt in vts:
            offs = hits[vt]
            print('-- vptr %08X (%s): %d 个实例 --'
                  % (vt, VTNAME.get(vt, '?'), len(offs)))
            for off in offs[:limit]:
                if off + 0x120 > len(d):
                    continue
                print('   @%08X  W=%-5d H=%-5d style=%08X B4=%-3d f8=%-4d font=%08X '
                      '9C=%-3d D9=%-3d 4C=%-5d top=%d'
                      % (off, u32(d, off + 0x40), u32(d, off + 0x44), u32(d, off + 0x1C),
                         d[off + 0xB4], u32(d, off + 0xF8), u32(d, off + 0x98),
                         u32(d, off + 0x9C), d[off + 0xD9], u32(d, off + 0x4C),
                         u32(d, off + 0x3C)))
            if len(offs) > limit:
                print('   … 还有 %d 个' % (len(offs) - limit))
        print()
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
