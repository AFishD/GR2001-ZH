# -*- coding: utf-8 -*-
"""summarise.py -- summarise a gsrunner watch.txt / hooklog.txt (read-only).

usage:
  python summarise.py watch <watch.txt>            # hits per watched addr, per frame
  python summarise.py hook  <hooklog.txt> [lo hi]  # lines per pc, per frame; optional cycle window
  python summarise.py ring  <watch.txt>            # writers + ring context per hit
"""
import sys
import re
from collections import Counter, defaultdict


def watch(path):
    per_addr = defaultdict(Counter)
    first_last = {}
    writers = defaultdict(Counter)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = re.match(r'hit (\d+) frame=(\d+) cycle=(\d+) addr=([0-9A-F]{8}) size=(\d+) '
                         r'writer_block=([0-9A-F]{8}) cur_block=([0-9A-F]{8}) old=(\S*) new=(\S*)', ln)
            if not m:
                continue
            n, fr, cyc, addr, size, wb, cb, old, new = m.groups()
            fr = int(fr)
            per_addr[addr][fr] += 1
            writers[addr][wb] += 1
            k = (addr, int(n))
            first_last[k] = (fr, int(cyc), wb, cb, old, new)
    for addr in sorted(per_addr):
        c = per_addr[addr]
        tot = sum(c.values())
        print('WATCH addr=%s hits=%d frames: %s' % (addr, tot,
              ' '.join('%d:%d' % (f, c[f]) for f in sorted(c))))
        print('   writers: %s' % ' '.join('%s x%d' % (w, n) for w, n in writers[addr].most_common()))
        ks = sorted([k for k in first_last if k[0] == addr], key=lambda k: k[1])
        print('   hit list (n:frame:cycle:writer:cur:old->new):')
        for k in ks:
            fr, cyc, wb, cb, old, new = first_last[k]
            print('     %3d f=%-4d c=%-12d w=%s cur=%s %s->%s' % (k[1], fr, cyc, wb, cb, old, new))


def hook(path, lo=None, hi=None):
    per_pc = defaultdict(Counter)
    rows = defaultdict(list)
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for ln in f:
            m = re.match(r'hook pc=([0-9A-F]{8}) frame=(\d+) cycle=(\d+) a0=([0-9A-F]{8}) a1=([0-9A-F]{8}) '
                         r'a2=([0-9A-F]{8}) a3=([0-9A-F]{8}) v0=([0-9A-F]{8}) s0=([0-9A-F]{8}) '
                         r's1=([0-9A-F]{8}) ra=([0-9A-F]{8}) sp=([0-9A-F]{8})', ln)
            if not m:
                continue
            g = m.groups()
            pc, fr, cyc = g[0], int(g[1]), int(g[2])
            if lo is not None and not (lo <= cyc <= hi):
                continue
            per_pc[pc][fr] += 1
            rows[(pc, fr)].append((cyc, g[3:]))
    for pc in sorted(per_pc):
        c = per_pc[pc]
        tot = sum(c.values())
        print('HOOK pc=%s lines=%d frames: %s' % (pc, tot,
              ' '.join('%d:%d' % (f, c[f]) for f in sorted(c))))
        for (p, fr) in sorted([k for k in rows if k[0] == pc], key=lambda k: k[1]):
            for (cyc, r) in rows[(p, fr)]:
                print('   f=%-4d c=%-12d a0=%s a1=%s a2=%s a3=%s v0=%s s0=%s s1=%s ra=%s sp=%s'
                      % (fr, cyc, *r))


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode = sys.argv[1]
    if mode == 'watch':
        watch(sys.argv[2])
    elif mode == 'hook':
        lo = int(sys.argv[3]) if len(sys.argv) > 3 else None
        hi = int(sys.argv[4]) if len(sys.argv) > 4 else None
        hook(sys.argv[2], lo, hi)
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
