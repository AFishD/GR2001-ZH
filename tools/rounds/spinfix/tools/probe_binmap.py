# -*- coding: utf-8 -*-
r"""probe_binmap.py —— 读三份现场（旧 dump / 新 dump / 存档原像）的 mstate 头与桶数组，
判定「坏桶 126 是否可达」（binmap 组位 bit31 = 组 31 = 桶 124..127）。READ-ONLY。
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
MSTATE = 0x0055B7A0
PSEUDO126 = 0x0055B798 + 8 * 126


def dump_state(ram, tag, out):
    bm, = struct.unpack_from('<Q', ram, MSTATE)
    top, = struct.unpack_from('<I', ram, MSTATE + 8)
    fd126, bk126 = struct.unpack_from('<II', ram, PSEUDO126 + 16)
    out.append('%s  mstate=0x%08X' % (tag, MSTATE))
    out.append('   [0x55B7A0] binmap(64) = 0x%016X   （低 32 位 0x%08X）'
               % (bm, bm & 0xFFFFFFFF))
    out.append('   组 30 (桶 120..123) 标记 = %d ; 组 31 (桶 124..127) 标记 = %d'
               % ((bm >> 30) & 1, (bm >> 31) & 1))
    out.append('   [0x55B7A8] top = 0x%08X' % top)
    out.append('   桶 126 伪 chunk 0x%08X: fd=%08X bk=%08X  %s'
               % (PSEUDO126, fd126, bk126,
                  '空桶自指' if fd126 == bk126 == PSEUDO126 else '★非空/已坏'))
    # 桶 120..127 全表
    for i in range(120, 128):
        p = 0x0055B798 + 8 * i
        f, b = struct.unpack_from('<II', ram, p + 16)
        out.append('   bin %3d  pseudo=%08X  fd=%08X bk=%08X  %s   bitmap_bit=%d'
                   % (i, p, f, b, 'empty' if f == b == p else 'NON-EMPTY',
                      (bm >> (i >> 2)) & 1))
    out.append('')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out = []
    for tag, f in (('OLD f19701 (健康)', os.path.join(
                        ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_19701_hotkey_f10\ee_ram.bin')),
                   ('NEW f23444 (桶126坏)', os.path.join(
                        ROOT, r'work\builds\GR_HOOKEMU_QT2\qt\hookdumps\hook_23444_hotkey_f10\ee_ram.bin'))):
        dump_state(open(f, 'rb').read(), tag, out)
    z = C.load_zstd_tool()
    for tag, f in (('STATE 7A761FCA (用户存档)', os.path.join(
            ROOT, r'work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s')),):
        dump_state(z.decompress_entry(f, 'eeMemory.bin'), tag, out)
    txt = '\n'.join(out)
    print(txt)
    with open(os.path.join(ROOT, 'work', 'builds', 'GR_SPINFIX', 'out', 'probe_binmap.txt'),
              'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
