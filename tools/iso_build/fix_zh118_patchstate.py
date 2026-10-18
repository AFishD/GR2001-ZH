# -*- coding: utf-8 -*-
r"""fix_zh118_patchstate.py — apply raw byte patches to a .p2s eeMemory.bin

Used to perturb the phantom code block at EE RAM address 0 (see
docs/REPORT_reclut_crash.md): if the r72 "unmapped recLUT" crash really comes
from executing the memcard-directory data at physical address 0, then changing
RAM[0] must change (or remove) the reported crash PC.

Usage:
  python tools/iso_build/fix_zh118_patchstate.py <src.p2s> <dst.p2s> \
      --set 0x00000000=03E00008 [--set addr=hexbytes ...]
"""
import argparse
import os
import sys
import zipfile

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fix_zh116_p2s as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('--set', action='append', default=[],
                    help='<addr>=<hexbytes> e.g. 0x00000000=03E00008')
    ap.add_argument('--set-file', default=None,
                    help='<addr>=<path> : write that file verbatim at addr')
    a = ap.parse_args()

    ram = bytearray(P.read_entry(a.src, 'eeMemory.bin'))
    print('eeMemory.bin = %d B' % len(ram))

    for spec in a.set:
        addr_s, hex_s = spec.split('=', 1)
        addr = int(addr_s, 0)
        data = bytes.fromhex(hex_s)
        print('  set RAM[%08X:%08X] = %s  (was %s)' %
              (addr, addr + len(data), data.hex().upper(),
               ram[addr:addr + len(data)].hex().upper()))
        ram[addr:addr + len(data)] = data

    if a.set_file:
        addr_s, path = a.set_file.split('=', 1)
        addr = int(addr_s, 0)
        data = open(path, 'rb').read()
        print('  set RAM[%08X:%08X] = %d bytes from %s' % (addr, addr + len(data), len(data), path))
        ram[addr:addr + len(data)] = data

    with zipfile.ZipFile(a.src) as z:
        infos = z.infolist()
    with zipfile.ZipFile(a.dst, 'w', zipfile.ZIP_DEFLATED) as out:
        for info in infos:
            data = bytes(ram) if info.filename == 'eeMemory.bin' else P.read_entry(a.src, info.filename)
            if info.filename == 'PCSX2 Savestate Version.id':
                out.writestr(zipfile.ZipInfo(info.filename), data, compress_type=zipfile.ZIP_STORED)
            else:
                out.writestr(info.filename, data, compress_type=zipfile.ZIP_DEFLATED)
    print('wrote %s (%d B)' % (a.dst, os.path.getsize(a.dst)))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
