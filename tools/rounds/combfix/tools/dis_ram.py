# -*- coding: utf-8 -*-
r"""dis_ram.py -- disassemble live EE RAM straight out of a hook dump (read-only).

Usage:
  python dis_ram.py <ram.bin> <loVA> <hiVA> [more pairs...]
  python dis_ram.py <ram.bin> --hex <VA> <len>
"""
import os
import sys
import struct
import importlib.util

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
_s = importlib.util.spec_from_file_location('cave_dis', os.path.join(ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    with open(sys.argv[1], 'rb') as f:
        ram = f.read()
    args = sys.argv[2:]
    if args and args[0] == '--hex':
        va = int(args[1], 16)
        n = int(args[2], 16) if len(args) > 2 else 64
        for base in range(va, va + n, 16):
            row = ram[(base & 0x1FFFFFFF):(base & 0x1FFFFFFF) + 16]
            print('%08X  %s  |%s|' % (base, ' '.join('%02X' % b for b in row),
                                      ''.join(chr(b) if 32 <= b < 127 else '.' for b in row)))
        return
    for i in range(0, len(args) - 1, 2):
        lo, hi = int(args[i], 16), int(args[i + 1], 16)
        print('=' * 96)
        print('# [0x%08X, 0x%08X)  (live RAM)' % (lo, hi))
        for va in range(lo, hi, 4):
            w = struct.unpack_from('<I', ram, va & 0x1FFFFFFF)[0]
            print('  %08x  %08x  %-46s ; %s' % (va, w, CD.dis(w, va), struct.pack('<I', w).hex()))


if __name__ == '__main__':
    main()
