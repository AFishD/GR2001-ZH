# -*- coding: utf-8 -*-
r"""root_dis.py -- round85 root-cause tool: disassemble the texture-load path.

Read-only.  Uses cave_dis.py's R5900-aware decoder + ELF loader.

CLI:
  python tools/re/toolbelt/root_dis.py sym                     # program headers
  python tools/re/toolbelt/root_dis.py dis  <loVA> <hiVA>
  python tools/re/toolbelt/root_dis.py word <VA>
  python tools/re/toolbelt/root_dis.py callers <VA>
  python tools/re/toolbelt/root_dis.py str <VA> [n]
  python tools/re/toolbelt/root_dis.py find  <hexbytes> [loVA] [hiVA]
  python tools/re/toolbelt/root_dis.py map   <VA>              # VA -> ISO offset (0x93800 + VA - 0x100080)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cave_dis  # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
ELF = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r72', 'SLUS_206.13.elf')
ISO_MAP_BASE = 0x93800 - 0x100080          # ISO = BASE + VA


def iso_off(va):
    return ISO_MAP_BASE + va


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    mode = sys.argv[1]
    e = cave_dis.Elf(ELF)
    if mode == 'sym':
        print('entry=0x%08X' % e.entry)
        for (v, o, fs) in e.segs:
            print('  PT_LOAD va=0x%08X off=0x%08X filesz=0x%08X  (va_end=0x%08X)' % (v, o, fs, v + fs))
        return 0
    if mode == 'map':
        va = int(sys.argv[2], 16)
        print('VA 0x%08X -> ISO 0x%X' % (va, iso_off(va)))
        return 0
    if mode == 'dis':
        lo, hi = int(sys.argv[2], 16), int(sys.argv[3], 16)
        for va in range(lo, hi, 4):
            try:
                w = e.word(va)
            except KeyError:
                print('  %08x  <outside PT_LOAD>' % va)
                continue
            print('  %08x  %08x  %s' % (va, w, cave_dis.dis(w, va)))
    elif mode == 'word':
        va = int(sys.argv[2], 16)
        w = e.word(va)
        print('0x%08X = 0x%08X  %s   (ISO 0x%X)' % (va, w, cave_dis.dis(w, va), iso_off(va)))
    elif mode == 'callers':
        t = int(sys.argv[2], 16)
        cs = cave_dis.callers(e, t)
        print('jal callers of 0x%08X : %d' % (t, len(cs)))
        for c in cs:
            print('   from 0x%08X' % c)
    elif mode == 'str':
        va = int(sys.argv[2], 16)
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 120
        b = e.read(va, n)
        z = b.find(b'\x00')
        print('0x%08X: %r' % (va, b[:z if z >= 0 else n]))
    elif mode == 'find':
        pat = bytes.fromhex(sys.argv[2])
        lo = int(sys.argv[3], 16) if len(sys.argv) > 3 else e.segs[0][0]
        hi = int(sys.argv[4], 16) if len(sys.argv) > 4 else e.segs[0][0] + e.segs[0][2]
        n = 0
        for va in range(lo, hi - len(pat) + 1, 4):
            if e.read(va, len(pat)) == pat:
                print('  hit 0x%08X' % va)
                n += 1
        print('total %d' % n)
    else:
        sys.stderr.write(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
