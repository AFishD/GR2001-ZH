# -*- coding: utf-8 -*-
r"""probe_f44.py —— 直接读「帧 44（失败 malloc 现场）」的运行时 32MB EE RAM 快照，
看运行期真正的 binmap / 桶 120..127 / top。READ-ONLY。

输入（默认）：
  work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000044_eeram.bin   （未修盘 + 原存档 + L1@30）
  work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000043_eeram.bin
  work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000045_eeram.bin
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sf_common as C   # noqa: E402

ROOT = C.ROOT
MSTATE = 0x0055B7A0


def show(ram, tag, out):
    bm, = struct.unpack_from('<Q', ram, MSTATE)
    top, = struct.unpack_from('<I', ram, MSTATE + 8)
    out.append('%s   binmap=0x%016X  top=0x%08X' % (tag, bm, top))
    for i in range(118, 128):
        p = 0x0055B798 + 8 * i
        f, b = struct.unpack_from('<II', ram, p + 16)
        out.append('    bin %3d fd=%08X bk=%08X %-9s bit=%d'
                   % (i, f, b, 'empty' if f == b == p else 'NON-EMPTY', (bm >> (i >> 2)) & 1))
    # 桶 1（unsorted）
    f1, b1 = struct.unpack_from('<II', ram, MSTATE + 16)
    out.append('    bin   1 fd=%08X bk=%08X %s' % (f1, b1, 'empty' if f1 == b1 == MSTATE else 'NON-EMPTY'))
    out.append('')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    out = []
    d = os.path.join(ROOT, r'work\builds\GR_OOMFIX\runs\u1_base_l1')
    for f in ('win_f00000043_eeram.bin', 'win_f00000044_eeram.bin',
              'win_f00000045_eeram.bin', 'win_f00000046_eeram.bin'):
        p = os.path.join(d, f)
        if not os.path.exists(p):
            out.append('[缺失] %s' % p)
            continue
        show(open(p, 'rb').read(), f, out)
    # 存档原像对照
    z = C.load_zstd_tool()
    st = os.path.join(ROOT, r'work\builds\GR_LAYOUT\SLUS-20613 (7A761FCA).01.p2s')
    show(z.decompress_entry(st, 'eeMemory.bin'), 'STATE(原像)', out)
    txt = '\n'.join(out)
    print(txt)
    with open(os.path.join(ROOT, 'work', 'builds', 'GR_SPINFIX', 'out', 'probe_f44.txt'),
              'w', encoding='utf-8', newline='\n') as fh:
        fh.write(txt + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
