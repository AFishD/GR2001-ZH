# -*- coding: utf-8 -*-
"""state_ram.py -- read a module out of a PCSX2 .p2s savestate (a plain ZIP) and
query EE RAM, without touching the original file.

usage:
  python state_ram.py dump   <state.p2s> <member> <out.bin>
  python state_ram.py words  <state.p2s> <addr> <n_words>
  python state_ram.py hexdump <state.p2s> <addr> <len>
  python state_ram.py list   <state.p2s>
"""
import struct
import sys
import zipfile


def ee(state):
    with zipfile.ZipFile(state) as z:
        return z.read('eeMemory.bin')


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    mode, state = sys.argv[1], sys.argv[2]
    if mode == 'list':
        with zipfile.ZipFile(state) as z:
            for i in z.infolist():
                print('   %-40s %10d' % (i.filename, i.file_size))
        return
    if mode == 'dump':
        with zipfile.ZipFile(state) as z:
            d = z.read(sys.argv[3])
        open(sys.argv[4], 'wb').write(d)
        print('wrote %d bytes -> %s' % (len(d), sys.argv[4]))
        return
    d = ee(state)
    a = int(sys.argv[3], 16)
    n = int(sys.argv[4], 16)
    if mode == 'words':
        for i in range(n):
            va = a + i * 4
            print('  %08X  %08X' % (va, struct.unpack_from('<I', d, va)[0]))
    elif mode == 'hexdump':
        for off in range(a, a + n, 16):
            chunk = d[off:off + 16]
            if not chunk:
                break
            print('  %08X  %-47s' % (off, ' '.join('%02X' % b for b in chunk)))
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
