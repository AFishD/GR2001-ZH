# -*- coding: utf-8 -*-
r"""hgA5b_hexdump.py — 只读: 把 FONT.RES 展开态「FontDefinition 之后」的区域按 16 B/行 hexdump。

产出: work/builds/GR_HUGE/evidence/hgA5b_hex.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    lines = []
    W = lines.append
    for tag in ('EN_ORIG', 'ZH113b'):
        d = H.fontres(tag, 'MENU')
        plain = d['plain']
        off = d['styles_off']
        W('=' * 90)
        W('%s/MENU  FontDefinition 之后 @0x%X  len=%d' % (tag, off, len(plain) - off))
        for i in range(off, len(plain), 16):
            chunk = plain[i:i + 16]
            asc = ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)
            W('  %04X  %-47s  %s' % (i, chunk.hex(' '), asc))
    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hgA5b_hex.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
