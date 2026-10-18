# -*- coding: utf-8 -*-
"""verify_sites.py -- read the ORIGINAL instruction words at candidate patch VA/ISO
sites from both discs (read-only) and prove the VA<->ISO mapping used by the fix table.

Mapping (LAY_fix1_bytecount / GR_REBUILD2400 family, ELF at LBA 295, first PT_LOAD
va=0x00100000 off=0x00000080):
    iso_off(va) = va - 0x00100000 + 0x80 + 295*2048 = va - 0x0006C780
Cross-checked against LAY_fix1_bytecount.meta.json: va 0x0021AC40 -> iso_off 0x001AE4C0.
"""
import struct
import sys

ROOT = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
LAY = ROOT + r'\work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso'
ENG = ROOT + r"\third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso"
ELF = ROOT + r'\work\builds\GR_CULPRIT\elf\LAY_fix1_bytecount_SLUS_206.13.elf'


def iso_off(va):
    return va - 0x100000 + 0x80 + 295 * 2048


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sites = [int(x, 16) for x in sys.argv[1:]] or [
        0x0021AC40, 0x0053916C, 0x00539174, 0x00539178, 0x0053917C, 0x005392A0,
        0x005392A4, 0x004039BC, 0x004039C8]
    f_lay = open(LAY, 'rb')
    f_eng = open(ENG, 'rb')
    f_elf = open(ELF, 'rb')
    print('%-10s %-10s %-10s %-10s %-10s %s' % ('VA', 'iso_off', 'ISO(LAY)', 'ISO(ENG)', 'ELF', 'match'))
    for va in sites:
        o = iso_off(va)
        f_lay.seek(o)
        wl = struct.unpack('<I', f_lay.read(4))[0]
        f_eng.seek(o)
        we = struct.unpack('<I', f_eng.read(4))[0]
        elf_off = va - 0x100000 + 0x80
        f_elf.seek(elf_off)
        wf = struct.unpack('<I', f_elf.read(4))[0]
        ok = 'LAY==ELF' if wl == wf else 'LAY!=ELF !!'
        if wl != we:
            ok += ' (ENG differs)'
        print('0x%08X 0x%08X %08X   %08X   %08X   %s' % (va, o, wl, we, wf, ok))


if __name__ == '__main__':
    main()
