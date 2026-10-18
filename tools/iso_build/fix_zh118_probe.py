# -*- coding: utf-8 -*-
r"""fix_zh118_probe.py — offline forensics on the r72 (recLUT) save state.

1. extracts eeMemory.bin (+ Scratchpad.bin) from a .p2s into an out dir
2. fingerprints which localized build the RAM came from (ELF byte match)
3. searches EE RAM for the wild-jump target value (0x0CAC6800) and for the
   containing 64 KB page id (0x0CAC) as a shifted/derived value
4. reports where the value sits relative to known bases

Usage:
  python tools/iso_build/fix_zh118_probe.py --state <p2s> --out <dir>
      [--value 0x0CAC6800] [--versions GR_ZH98,GR_ZH109,GR_ZH111,...]
"""
import argparse
import os
import struct
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import fix_zh116_p2s as P  # noqa: E402
import tcslib  # noqa: E402

BUILDS = os.path.join(REPO, 'work', 'builds')
ELF_LBA = 295
ELF_SIZE = 37453732
SEG_OFF = 0x80        # main segment file offset inside the ELF
SEG_PADDR = 0x100000  # where it lands in EE RAM
SEG_FILESZ = 5106944


def elf_of(ver):
    iso = os.path.join(BUILDS, ver, '%s.iso' % ver)
    if not os.path.isfile(iso):
        return None
    f = tcslib.Iso(iso)
    try:
        return f.read(ELF_LBA * 2048, ELF_SIZE)
    finally:
        f.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--state', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--value', default='0x0CAC6800')
    ap.add_argument('--versions', default='GR_ZH98,GR_ZH109,GR_ZH111,GR_ZH113,GR_ZH113b,GR_ZH115,GR_ZH117,GR_EN_ORIG')
    a = ap.parse_args()

    val = int(a.value, 0)
    os.makedirs(a.out, exist_ok=True)

    print('== entries in %s ==' % a.state)
    for name in ('PCSX2 Savestate Version.id', 'Screenshot.png', 'eeMemory.bin'):
        try:
            b = P.read_entry(a.state, name)
            print('   %-32s %d B' % (name, len(b)))
        except KeyError:
            print('   %-32s MISSING' % name)

    ram = P.read_entry(a.state, 'eeMemory.bin')
    ramp = os.path.join(a.out, 'eeMemory.bin')
    with open(ramp, 'wb') as f:
        f.write(ram)
    print('   eeMemory.bin -> %s (%d B)' % (ramp, len(ram)))
    try:
        sp = P.read_entry(a.state, 'Scratchpad.bin')
        with open(os.path.join(a.out, 'Scratchpad.bin'), 'wb') as f:
            f.write(sp)
        print('   Scratchpad.bin -> %d B' % len(sp))
    except KeyError:
        pass

    # ---- 2) which build does the RAM carry? ----
    print('\n== ELF fingerprint (RAM[%08X+i] vs ISO ELF[%#x+i]) ==' % (SEG_PADDR, SEG_OFF))
    vers = [v.strip() for v in a.versions.split(',') if v.strip()]
    elfs = {}
    for v in vers:
        b = elf_of(v)
        if b is None:
            print('   !! missing ISO %s' % v)
            continue
        elfs[v] = b
    n = min(SEG_FILESZ, len(ram) - SEG_PADDR)
    # discriminative offsets = bytes where the candidates disagree
    diff = []
    for i in range(n):
        s = {elfs[v][SEG_OFF + i] for v in elfs}
        if len(s) > 1:
            diff.append(i)
    print('   discriminative offsets: %d' % len(diff))
    for v in sorted(elfs):
        tot_eq = sum(1 for i in range(n) if ram[SEG_PADDR + i] == elfs[v][SEG_OFF + i])
        dm = sum(1 for i in diff if ram[SEG_PADDR + i] == elfs[v][SEG_OFF + i])
        print('   %-12s overall %6d/%6d = %5.1f%%   discriminative %6d/%6d' %
              (v, tot_eq, n, 100.0 * tot_eq / n, dm, len(diff)))
    if diff:
        base = 'GR_ZH111' if 'GR_ZH111' in elfs else sorted(elfs)[0]
        z = elfs[base]
        nz = sum(1 for i in diff if ram[SEG_PADDR + i] != z[SEG_OFF + i])
        print('   RAM differs from %s at %d of the discriminative offsets' % (base, nz))

    # ---- 3) where does the wild jump target live in RAM? ----
    print('\n== search EE RAM for value %08X ==' % val)
    pat = struct.pack('<I', val)
    hits = []
    st = 0
    while True:
        k = ram.find(pat, st)
        if k < 0:
            break
        hits.append(k)
        st = k + 1
        if len(hits) > 400:
            break
    print('   little-endian hits: %d' % len(hits))
    for k in hits[:60]:
        print('     RAM[%08X]' % k)
    if len(hits) > 60:
        print('     ... (%d more)' % (len(hits) - 60))

    # upper-half / shifted variants
    for label, v in (('page id 0x%04X as u32' % (val >> 16), val >> 16),
                     ('val/4', val // 4), ('val/8', val // 8), ('val as float bits', None)):
        if v is None:
            continue
        p2 = struct.pack('<I', v)
        c = ram.count(p2)
        print('   %-28s (%08X) hits=%d' % (label, v, c))
        if 0 < c <= 8:
            st = 0
            while True:
                k = ram.find(p2, st)
                if k < 0:
                    break
                print('        RAM[%08X]' % k)
                st = k + 1

    print('\n== scratchpad search for %08X ==' % val)
    try:
        sp = P.read_entry(a.state, 'Scratchpad.bin')
        print('   hits: %d' % sp.count(pat))
    except KeyError:
        print('   (no scratchpad entry)')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    main()
