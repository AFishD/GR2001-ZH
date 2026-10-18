# -*- coding: utf-8 -*-
r"""probe.py -- read EE RAM from a PCSX2 .p2s savestate (zip member eeMemory.bin)
or from a raw 32 MiB EE RAM dump, and dump words/bytes.  READ-ONLY on inputs.

usage:
  python probe.py list   <state.p2s>
  python probe.py extract <state.p2s> <out.bin>
  python probe.py words  <ram.bin|state.p2s> <addr_hex> <count>
  python probe.py hex    <ram.bin|state.p2s> <addr_hex> <len>
  python probe.py ptrs   <ram.bin|state.p2s> <addr_hex> <count>
"""
import struct
import sys
import zipfile

RAM_SIZE = 32 * 1024 * 1024


def load(path):
    if path.lower().endswith('.p2s'):
        with zipfile.ZipFile(path) as z:
            d = z.read('eeMemory.bin')
    else:
        with open(path, 'rb') as f:
            d = f.read()
    if len(d) < RAM_SIZE:
        raise SystemExit('short image: %d' % len(d))
    return d


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode = sys.argv[1]
    if mode == 'list':
        with zipfile.ZipFile(sys.argv[2]) as z:
            for i in z.infolist():
                print('   %-40s %10d' % (i.filename, i.file_size))
        return
    if mode == 'extract':
        d = load(sys.argv[2])
        with open(sys.argv[3], 'wb') as f:
            f.write(d)
        print('wrote %d bytes -> %s' % (len(d), sys.argv[3]))
        return
    d = load(sys.argv[2])
    a = int(sys.argv[3], 16)
    n = int(sys.argv[4], 0)
    if mode == 'words':
        for i in range(n):
            va = a + i * 4
            print('  %08X  %08X' % (va, struct.unpack_from('<I', d, va)[0]))
    elif mode == 'ptrs':
        for i in range(n):
            va = a + i * 4
            v = struct.unpack_from('<I', d, va)[0]
            tag = ''
            if 0 < v < RAM_SIZE:
                tag = '  <ram>'
            print('  %08X  %08X%s' % (va, v, tag))
    elif mode == 'hex':
        for off in range(a, a + n, 16):
            chunk = d[off:off + 16]
            if not chunk:
                break
            print('  %08X  %s  |%s|' % (off, ' '.join('%02X' % b for b in chunk),
                                        ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
