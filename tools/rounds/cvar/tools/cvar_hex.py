# -*- coding: utf-8 -*-
r"""cvar_hex.py — 打印两个 ISO 在指定 ISO 区间/相对 IMG 偏移处的十六进制对照

用法:
  python cvar_hex.py --a A --b B --iso-off 0x... --len 512
  python cvar_hex.py --a A --b B --img MENU.IMG --rel 0x57400 --len 512
  python cvar_hex.py --a A --b B --img MENU.IMG --entry 3 --len 512
"""
import argparse
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--a', required=True)
    ap.add_argument('--b', required=True)
    ap.add_argument('--iso-off', default=None)
    ap.add_argument('--img', default=None)
    ap.add_argument('--rel', default=None)
    ap.add_argument('--entry', type=int, default=None)
    ap.add_argument('--len', type=int, default=256)
    x = ap.parse_args()
    A = open(x.a, 'rb').read()
    B = open(x.b, 'rb').read()
    if x.iso_off:
        off = int(x.iso_off, 16)
    else:
        lba = IMG_LBA[x.img]
        b = lba * SEC
        if x.entry is not None:
            f = list(struct.unpack_from('<12I', A, b + TAB_OFF + TAB_STEP * x.entry))
            off = b + f[8]
            print('entry #%d off=0x%X stored=0x%X real=0x%X' % (x.entry, f[8], f[6], f[7]))
        else:
            off = b + int(x.rel, 16)
    print('ISO 0x%X  len %d' % (off, x.len))
    for base in range(0, x.len, 16):
        o = off + base
        da, db = A[o:o + 16], B[o:o + 16]
        mark = '' if da == db else '  <<<'
        print('  0x%09X  A %s  |%s|' % (o, da.hex(' '), ''.join(
            chr(c) if 32 <= c < 127 else '.' for c in da)))
        if da != db:
            print('             B %s  |%s|%s' % (db.hex(' '), ''.join(
                chr(c) if 32 <= c < 127 else '.' for c in db), mark))
    return 0


if __name__ == '__main__':
    sys.exit(main())
