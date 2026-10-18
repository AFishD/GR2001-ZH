# -*- coding: utf-8 -*-
"""ramq.py -- query the 32 MB EE RAM dumps (read-only).

usage:
  python ramq.py hexdump <eeram.bin> <addr> <len>
  python ramq.py find    <eeram.bin> <hexvalue_u32> [<hexvalue_u32> ...]
  python ramq.py words   <eeram.bin> <addr> <n_words>
"""
import struct
import sys


def load(p):
    with open(p, 'rb') as f:
        return f.read()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode, path = sys.argv[1], sys.argv[2]
    d = load(path)
    if mode == 'hexdump':
        a = int(sys.argv[3], 16)
        n = int(sys.argv[4], 16)
        for off in range(a, a + n, 16):
            chunk = d[off:off + 16]
            if not chunk:
                break
            hx = ' '.join('%02X' % b for b in chunk)
            asc = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print('  %08X  %-47s  %s' % (off, hx, asc))
    elif mode == 'words':
        a = int(sys.argv[3], 16)
        n = int(sys.argv[4])
        for i in range(n):
            va = a + i * 4
            w = struct.unpack_from('<I', d, va)[0]
            print('  %08X  %08X' % (va, w))
    elif mode == 'find':
        want = [int(x, 16) & 0xFFFFFFFF for x in sys.argv[3:]]
        packs = [struct.pack('<I', w) for w in want]
        hits = {w: [] for w in want}
        for i, w in enumerate(want):
            start = 0
            pat = packs[i]
            while True:
                j = d.find(pat, start)
                if j < 0:
                    break
                hits[w].append(j)
                start = j + 1
        for w in want:
            ls = hits[w]
            print('value %08X : %d hits%s' % (w, len(ls),
                  (' -> ' + ' '.join('%08X' % x for x in ls[:40])) if ls else ''))
            if len(ls) > 40:
                print('    (first 40 shown, more...)')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
