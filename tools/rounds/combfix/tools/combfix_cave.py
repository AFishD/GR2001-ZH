# -*- coding: utf-8 -*-
r"""combfix_cave.py -- find + audit a zero cave for the F1b station (READ-ONLY).

Criteria (same method as GR_SPINFIX/GR_OOMFIX cave audits):
  * >= min_len consecutive zero bytes inside the single PT_LOAD segment (VA 0x100000..)
  * no 'j'/'jal' target anywhere in the loaded segment points into the region
  * no 32-bit literal equal to an address inside the region
  * not inside any known-used window
  * byte-identical zero in every runtime snapshot given (dumps / savestate eeMemory)
  * report the nearest preceding/following bytes so the report can argue "dead zone"

Usage:
  python combix_cave.py --min 0x48 --top 12 [--json out.json]
"""
import argparse
import json
import os
import struct
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
ELF = os.path.join(ROOT, 'work', 'builds', 'GR_CULPRIT', 'elf', 'LAY_fix1_bytecount_SLUS_206.13.elf')
DUMPS = os.path.join(ROOT, 'work', 'builds', 'GR_HOOKEMU_QT2', 'qt', 'hookdumps')
SNAPSHOTS = [
    os.path.join(DUMPS, 'hook_10470_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_13112_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_14025_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_16893_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_19095_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_19671_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_19701_hotkey_f10', 'ee_ram.bin'),
    os.path.join(DUMPS, 'hook_23444_hotkey_f10', 'ee_ram.bin'),
]
ISO_OF_VA = 0x6C780
LOAD_VA = 0x00100000
LOAD_END = 0x00100000 + 0x004DED00

USED = [
    (0x00416E00, 0x00417800, 'DBCS cave'),
    (0x00416EE8, 0x00416EF0, 'gate1'),
    (0x00417160, 0x00417168, 'gate2'),
    (0x0041751C, 0x00417524, 'gate3'),
    (0x005656A4, 0x005656AC, 'gate4'),
    (0x00565600, 0x00565B00, 'ZH cave block B'),
    (0x00550048, 0x00550080, 'OOMFIX cave (F1+F2)'),
    (0x00539110, 0x00539310, 'decompressor'),
    (0x0051BE10, 0x0051C000, 'decompressor caller'),
    (0x0021AC00, 0x0021AE00, 'RSFont replaced'),
    (0x00101C00, 0x00102700, 'allocator'),
    (0x0055B730, 0x0055B780, 'SPINFIX CAVE_F1'),
    (0x005DECC4, 0x005DED00, 'SPINFIX CAVE_F2'),
    (0x0041A35C, 0x0041A380, 'SPINFIX CAVE_F4'),
]


def load_dumps():
    ram = []
    for p in SNAPSHOTS:
        if os.path.exists(p):
            with open(p, 'rb') as f:
                ram.append((os.path.basename(os.path.dirname(p)), f.read()))
    return ram


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    ap = argparse.ArgumentParser()
    ap.add_argument('--min', default='0x48')
    ap.add_argument('--top', type=int, default=12)
    ap.add_argument('--json', default=None)
    a = ap.parse_args()
    min_len = int(a.min, 16) if a.min.lower().startswith('0x') else int(a.min)

    with open(ELF, 'rb') as f:
        elf = f.read()

    def va2off(va):
        return va - ISO_OF_VA

    body_off = va2off(LOAD_VA)
    body_end = va2off(LOAD_END)
    body = elf[body_off:body_end]

    # ---- zero runs ----
    runs = []
    i = 0
    n = len(body)
    while i < n:
        if body[i] == 0:
            j = i
            while j < n and body[j] == 0:
                j += 1
            if j - i >= min_len:
                runs.append((LOAD_VA + i, LOAD_VA + j))
            i = j
        else:
            i += 1
    print('[scan] zero runs >= %d B in loaded segment: %d' % (min_len, len(runs)))

    # ---- control-transfer targets (op 2/3) over the whole loaded segment ----
    targets = set()
    for k in range(0, n - 3, 4):
        w = struct.unpack_from('<I', body, k)[0]
        if (w >> 26) in (2, 3):
            targets.add(((w & 0x03FFFFFF) << 2) | ((LOAD_VA + k) & 0xF0000000))
    print('[scan] j/jal targets: %d' % len(targets))

    # ---- 32-bit literals inside the loaded segment ----
    lits = set()
    for k in range(0, n - 3, 4):
        w = struct.unpack_from('<I', body, k)[0]
        if LOAD_VA <= w < LOAD_END:
            lits.add(w)
    print('[scan] 32-bit literals pointing into the segment: %d' % len(lits))

    dumps = load_dumps()
    print('[scan] runtime snapshots: %d' % len(dumps))

    cands = []
    for (lo, hi) in runs:
        used = [u for u in USED if not (hi <= u[0] or lo >= u[1])]
        if used:
            continue
        tg = [t for t in targets if lo <= t < hi]
        lt = [l for l in lits if lo <= l < hi]
        nonz = []
        for (nm, ram) in dumps:
            seg = ram[(lo & 0x1FFFFFFF):(hi & 0x1FFFFFFF)]
            nz = sum(1 for b in seg if b)
            if nz:
                nonz.append('%s:%d' % (nm, nz))
        cands.append(dict(va_lo='0x%08X' % lo, va_hi='0x%08X' % hi, size=hi - lo,
                          iso_off='0x%08X' % va2off(lo), elf_off='0x%07X' % va2off(lo),
                          jtargets=len(tg), literals=len(lt), nonzero_in_dumps=nonz))

    cands.sort(key=lambda c: (-c['size'], int(c['va_lo'], 16)))
    print('\n[candidates] %d (sorted by size desc)' % len(cands))
    for c in cands[:a.top]:
        va = int(c['va_lo'], 16)
        pre = elf[va2off(va) - 16:va2off(va)]
        post = elf[va2off(va) + c['size']:va2off(va) + c['size'] + 16]
        print('  %s..%s  %4d B  jt=%d lit=%d nonzero=%s' % (
            c['va_lo'], c['va_hi'], c['size'], c['jtargets'], c['literals'],
            c['nonzero_in_dumps'] or 'none'))
        print('       pre=%s post=%s' % (pre.hex(), post.hex()))
    if a.json:
        with open(a.json, 'w', encoding='utf-8') as f:
            json.dump(cands, f, indent=1, ensure_ascii=False)
        print('wrote', a.json)


if __name__ == '__main__':
    main()
