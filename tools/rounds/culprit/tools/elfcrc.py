# -*- coding: utf-8 -*-
"""elfcrc.py -- PCSX2 ElfObject::GetCRC() (XOR of all u32 words) for ELFs / ISOs.

PCSX2 savestate names are "<serial> (<CRC8hex>).NN.p2s" where CRC is this value,
so this identifies which disc/build a savestate belongs to.

usage:
  python elfcrc.py <elf-or-iso> [...]
     for an .iso the SLUS_206.13 (or first SLUS*) entry is extracted from the
     ISO9660 root directory and hashed (read-only).
"""
import os
import struct
import sys

SECTOR = 2048


def xor_crc(data):
    n = len(data) // 4
    c = 0
    for (w,) in struct.iter_unpack('<I', data[:n * 4]):
        c ^= w
    return c & 0xFFFFFFFF


def iso_root(path):
    with open(path, 'rb') as f:
        f.seek(16 * SECTOR)
        pvd = f.read(SECTOR)
        if pvd[1:6] != b'CD001':
            raise SystemExit('%s: not an ISO9660 image' % path)
        rlba = struct.unpack_from('<I', pvd, 156 + 2)[0]
        rsz = struct.unpack_from('<I', pvd, 156 + 10)[0]
        f.seek(rlba * SECTOR)
        d = f.read(rsz)
    ents = []
    off = 0
    while off < len(d):
        rl = d[off]
        if rl == 0:
            break
        nm = d[off + 33:off + 33 + d[off + 32]].decode('latin-1').split(';')[0]
        lba = struct.unpack_from('<I', d, off + 2)[0]
        sz = struct.unpack_from('<I', d, off + 10)[0]
        ents.append((nm, lba, sz))
        off += rl
    return ents


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    for p in sys.argv[1:]:
        if p.lower().endswith('.iso'):
            for (nm, lba, sz) in iso_root(p):
                if not nm.upper().startswith('SLUS'):
                    print('   %-14s lba=%-8d size=%d  (skipped: not the game ELF)' % (nm, lba, sz))
                    continue
                with open(p, 'rb') as f:
                    f.seek(lba * SECTOR)
                    d = f.read(sz)
                print('   %-14s lba=%-8d size=%-9d CRC=%08X' % (nm, lba, sz, xor_crc(d)))
        else:
            d = open(p, 'rb').read()
            print('   %-70s size=%-9d CRC=%08X' % (os.path.basename(p), len(d), xor_crc(d)))


if __name__ == '__main__':
    main()
