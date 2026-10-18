# -*- coding: utf-8 -*-
r"""pxdiff.py -- pixel stats for differing snapshots between two smoke runs.

Usage: python pxdiff.py <dirA> <dirB> [frames...]
"""
import hashlib
import os
import re
import sys

from PIL import Image, ImageChops

SNAP = re.compile(r'^snap_f(\d+)\.png$')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    A, B = sys.argv[1], sys.argv[2]
    want = [int(x) for x in sys.argv[3:]] or None
    frames = []
    for n in os.listdir(A):
        m = SNAP.match(n)
        if m and (want is None or int(m.group(1)) in want):
            frames.append(int(m.group(1)))
    frames.sort()
    for f in frames:
        pa = os.path.join(A, 'snap_f%08d.png' % f)
        pb = os.path.join(B, 'snap_f%08d.png' % f)
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print('f=%d: missing file' % f)
            continue
        if open(pa, 'rb').read() == open(pb, 'rb').read():
            print('f=%-5d identical' % f)
            continue
        ia = Image.open(pa).convert('RGB')
        ib = Image.open(pb).convert('RGB')
        if ia.size != ib.size:
            print('f=%-5d size differs %s vs %s' % (f, ia.size, ib.size))
            continue
        d = ImageChops.difference(ia, ib)
        bbox = d.getbbox()
        hist = d.histogram()
        # per-channel diff pixel counts
        px = list(d.getdata())
        ndiff = sum(1 for p in px if p != (0, 0, 0))
        maxd = 0
        for p in px:
            m = max(p)
            if m > maxd:
                maxd = m
        print('f=%-5d size=%s diff_px=%d (%.4f%%) bbox=%s maxdelta=%d' % (
            f, ia.size, ndiff, 100.0 * ndiff / (ia.size[0] * ia.size[1]), bbox, maxd))


if __name__ == '__main__':
    main()
