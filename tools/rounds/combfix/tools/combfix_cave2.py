# -*- coding: utf-8 -*-
r"""combfix_cave2.py -- refined cave search: find sub-runs that are zero in the ELF *and*
zero in every runtime snapshot inside larger zero runs (READ-ONLY).

For each zero run >= --run of the loaded segment:
  * dirty = union over snapshots of positions with non-zero bytes
  * clean sub-runs = run minus dirty
  * keep sub-runs with len >= --min, no j/jal target and no 32-bit literal inside
Usage: python combfix_cave2.py --run 0x40 --min 0x28
"""
import os
import struct
import sys
import json

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
ELF = os.path.join(ROOT, 'work', 'builds', 'GR_CULPRIT', 'elf', 'LAY_fix1_bytecount_SLUS_206.13.elf')
DUMPS = os.path.join(ROOT, 'work', 'builds', 'GR_HOOKEMU_QT2', 'qt', 'hookdumps')
SNAPS = [os.path.join(DUMPS, d, 'ee_ram.bin') for d in
         ['hook_10470_hotkey_f10', 'hook_13112_hotkey_f10', 'hook_14025_hotkey_f10',
          'hook_16893_hotkey_f10', 'hook_19095_hotkey_f10', 'hook_19671_hotkey_f10',
          'hook_19701_hotkey_f10', 'hook_23444_hotkey_f10']]
ISO_OF_VA = 0x6C780
LOAD_VA = 0x00100000
LOAD_END = 0x00100000 + 0x004DED00
USED = [
    (0x00416E00, 0x00417800, 'DBCS cave'),
    (0x00565600, 0x00565B00, 'ZH cave block B'),
    (0x00550048, 0x00550080, 'OOMFIX cave'),
    (0x00539110, 0x00539310, 'decompressor'),
    (0x0051BE10, 0x0051C000, 'decompressor caller'),
    (0x0021AC00, 0x0021AE00, 'RSFont replaced'),
    (0x00101C00, 0x00102700, 'allocator'),
    (0x0055B730, 0x0055B780, 'SPINFIX CAVE_F1'),
    (0x005DECC4, 0x005DED00, 'SPINFIX CAVE_F2'),
    (0x0041A35C, 0x0041A380, 'SPINFIX CAVE_F4'),
]


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    run_min = 0x40
    min_len = 0x28
    if '--run' in sys.argv:
        run_min = int(sys.argv[sys.argv.index('--run') + 1], 0)
    if '--min' in sys.argv:
        min_len = int(sys.argv[sys.argv.index('--min') + 1], 0)

    elf = open(ELF, 'rb').read()
    body = elf[ISO_OF_VA:ISO_OF_VA + (LOAD_END - LOAD_VA)]
    rams = []
    for p in SNAPS:
        if os.path.exists(p):
            rams.append((os.path.basename(os.path.dirname(p)), open(p, 'rb').read()))
    n = len(body)

    # zero runs in the ELF
    runs = []
    i = 0
    while i < n:
        if body[i] == 0:
            j = i
            while j < n and body[j] == 0:
                j += 1
            if j - i >= run_min:
                runs.append((i, j))
            i = j
        else:
            i += 1

    # control targets / literals
    targets, lits = set(), set()
    for k in range(0, n - 3, 4):
        w = struct.unpack_from('<I', body, k)[0]
        if (w >> 26) in (2, 3):
            targets.add(((w & 0x03FFFFFF) << 2) | ((LOAD_VA + k) & 0xF0000000))
        if LOAD_VA <= w < LOAD_END:
            lits.add(w)

    out = []
    for (a, b) in runs:
        va = LOAD_VA + a
        dirty = set()
        for (nm, ram) in rams:
            seg = ram[(va & 0x1FFFFFFF):(va & 0x1FFFFFFF) + (b - a)]
            for off, byte in enumerate(seg):
                if byte:
                    dirty.add(off)
        # clean sub-runs
        s = 0
        while s < (b - a):
            if s in dirty:
                s += 1
                continue
            e = s
            while e < (b - a) and e not in dirty:
                e += 1
            if e - s >= min_len:
                cva, cvb = LOAD_VA + a + s, LOAD_VA + a + e
                used = [u for u in USED if not (cvb <= u[0] or cva >= u[1])]
                tg = [t for t in targets if cva <= t < cvb]
                lt = [l for l in lits if cva <= l < cvb]
                out.append(dict(va_lo='0x%08X' % cva, va_hi='0x%08X' % cvb, size=cvb - cva,
                                iso_off='0x%08X' % (cva - ISO_OF_VA),
                                elf_off='0x%07X' % (cva - ISO_OF_VA),
                                used_overlap=[u[2] for u in used], jtargets=len(tg), literals=len(lt),
                                dirty_in_outer_run=len(dirty)))
            s = e + 1

    out.sort(key=lambda x: (-x['size'], int(x['va_lo'], 16)))
    print('[scan] zero runs >= %d: %d ; clean sub-runs >= %d: %d' % (run_min, len(runs), min_len, len(out)))
    for x in out[:40]:
        print('  %s..%s %4d B  jt=%d lit=%d used=%s (outer dirty bytes=%d)' % (
            x['va_lo'], x['va_hi'], x['size'], x['jtargets'], x['literals'],
            x['used_overlap'] or '-', x['dirty_in_outer_run']))
    with open(os.path.join(ROOT, 'work', 'builds', 'GR_COMBFIX', 'out', 'cave_clean_subruns.json'),
              'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print('wrote out/cave_clean_subruns.json')


if __name__ == '__main__':
    main()
