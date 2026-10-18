# -*- coding: utf-8 -*-
r"""r69_rshtml.py — 汇总多个 EE RAM 转储里 RSHTML / RSTextComponent 实例分布。

用法: python r69_rshtml.py <eeram.bin> [...] [--full]
"""
import os
import struct
import sys

VT_RSHTML = 0x005978C0
VT_RSTEXT = 0x005979E0
VTNAME = {VT_RSHTML: 'RSHTML', VT_RSTEXT: 'RSTextComponent'}


def u32(d, off):
    return struct.unpack_from('<I', d, off)[0]


def main():
    full = '--full' in sys.argv
    paths = [a for a in sys.argv[1:] if not a.startswith('--')]
    for path in paths:
        d = open(path, 'rb').read()
        groups = {VT_RSHTML: [], VT_RSTEXT: []}
        for off in range(0, len(d) - 4, 4):
            v = u32(d, off)
            if v in groups:
                groups[v].append(off)
        print('===== %s =====' % os.path.basename(path))
        h = groups[VT_RSHTML]
        print('  RSHTML 实例 %d 个:' % len(h))
        for off in h:
            print('     @%08X W=%-5d H=%-5d style=%08X B4=%-3d f8=%-4d 9C=%-3d D9=%-4d 4C=%-4d top=%d'
                  % (off, u32(d, off + 0x40), u32(d, off + 0x44), u32(d, off + 0x1C),
                     d[off + 0xB4], u32(d, off + 0xF8), u32(d, off + 0x9C),
                     u32(d, off + 0xD9), u32(d, off + 0x4C), u32(d, off + 0x3C)))
        t = groups[VT_RSTEXT]
        print('  RSTextComponent 实例 %d 个' % len(t))
        if full:
            for off in t:
                print('     @%08X W=%-5d H=%-5d style=%08X B4=%-3d f8=%-4d 9C=%-3d top=%d'
                      % (off, u32(d, off + 0x40), u32(d, off + 0x44), u32(d, off + 0x1C),
                         d[off + 0xB4], u32(d, off + 0xF8), u32(d, off + 0x9C),
                         u32(d, off + 0x3C)))
        # 反查: 有谁"指向" RSHTML 实例 (父对象)
        for off in h:
            refs = []
            pat = struct.pack('<I', off)
            p = d.find(pat)
            while p >= 0 and len(refs) < 6:
                refs.append(p)
                p = d.find(pat, p + 1)
            print('     引用 @%08X 的字段: %s' % (off, ['%08X' % r for r in refs[:6]]))
        print()
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.exit(main())
