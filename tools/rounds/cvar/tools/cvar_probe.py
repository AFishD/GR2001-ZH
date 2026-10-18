# -*- coding: utf-8 -*-
r"""cvar_probe.py — 定点: 打印 IMG 条目表若干条目 + 指定 ISO 区间的原始/差异字节

用法:
  python cvar_probe.py --iso <iso> --img MENU.IMG --entries 0-40
  python cvar_probe.py --a <A> --b <B> --runs <json> --range 0x..-0x..
"""
import argparse
import json
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}
TAG = ['+0x00', '+0x04', '+0x08', '+0x0C', '+0x10', '+0x14', '+0x18 STORED',
       '+0x1C REAL', '+0x20 OFF', '+0x24', '+0x28', '+0x2C']


def ents(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    return [(nm, list(struct.unpack_from('<12I', d, b + TAB_OFF + TAB_STEP * i)))
            for i, nm in enumerate(names)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso')
    ap.add_argument('--img', default='MENU.IMG')
    ap.add_argument('--entries', default=None, help='如 0-40 或 30,282')
    ap.add_argument('--a')
    ap.add_argument('--b')
    ap.add_argument('--runs')
    ap.add_argument('--range', default=None, help='0xSTART-0xEND')
    ap.add_argument('--find-name', default=None)
    x = ap.parse_args()

    if x.iso:
        d = open(x.iso, 'rb').read()
        lba = IMG_LBA[x.img]
        b = lba * SEC
        h = struct.unpack_from('<8I', d, b)
        print('%s @LBA %d iso=0x%X  hdr=%s' % (x.img, lba, b,
              ' '.join('+0x%02X=%d(0x%X)' % (4 * i, v, v) for i, v in enumerate(h))))
        E = ents(d, lba)
        print('条目数 %d ; 条目表 [0x%X,0x%X) ISO 0x%X..0x%X'
              % (len(E), TAB_OFF, TAB_OFF + TAB_STEP * len(E), b + TAB_OFF,
                 b + TAB_OFF + TAB_STEP * len(E)))
        if x.find_name:
            for i, (nm, f) in enumerate(E):
                if x.find_name.lower() in nm.lower():
                    print('  [%4d] %-24s %s' % (i, nm, ' '.join(
                        '%s=%d(0x%X)' % (TAG[j], v, v) for j, v in enumerate(f))))
        if x.entries:
            if '-' in x.entries:
                lo, hi = x.entries.split('-')
                idx = range(int(lo), int(hi))
            else:
                idx = [int(v) for v in x.entries.split(',')]
            for i in idx:
                nm, f = E[i]
                print('  [%4d] %-24s tab@ISO 0x%X  %s' % (
                    i, nm, b + TAB_OFF + TAB_STEP * i,
                    ' '.join('%s=%d(0x%X)' % (TAG[j], v, v) for j, v in enumerate(f))))
    if x.a and x.b and x.runs and x.range:
        s, e = x.range.split('-')
        s, e = int(s, 16), int(e, 16)
        A = open(x.a, 'rb').read()
        B = open(x.b, 'rb').read()
        D = json.load(open(x.runs, encoding='utf-8'))
        sel = [(a, b2) for a, b2 in D['runs'] if a >= s and b2 <= e]
        print('区间 0x%X..0x%X 内差异游程 %d 个, 合计 %d B'
              % (s, e, len(sel), sum(b2 - a for a, b2 in sel)))
        for a, b2 in sel[:200]:
            print('  0x%09X (+0x%X, len %d):  A=%s  B=%s'
                  % (a, a - s, b2 - a, A[a:b2].hex(), B[a:b2].hex()))
        if len(sel) > 200:
            print('  ... 还有 %d' % (len(sel) - 200))
    return 0


if __name__ == '__main__':
    sys.exit(main())
