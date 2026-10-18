# -*- coding: utf-8 -*-
import sys, struct
sys.path.insert(0, r"tools\rounds\oomfix\tools")
sys.path.insert(0, r"tools\re\toolbelt")
from oomfix_cave import read_elf, Elf, func_ranges, reloc_offsets
from cave_dis import dis

CANDS = [(0x00550048, 0x00550080), (0x005DECC4, 0x005DED00), (0x0055B730, 0x0055B780)]
for iso in (r"work\builds\GR_REBUILD\GR_REBUILD2400.iso", r"work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso"):
    data, lba, size = read_elf(iso)
    e = Elf(data)
    print("=" * 100)
    print(iso, " ELF sha256=", __import__("hashlib").sha256(data).hexdigest())
    syms = e.syms()
    fr = func_ranges(e)
    for (lo, hi) in CANDS:
        blob = data[e.va2off(lo):e.va2off(lo) + (hi - lo)]
        print("-- candidate 0x%08X..0x%08X (%d B) all-zero=%s" % (lo, hi, hi-lo, set(blob) <= {0}))
        # symbols containing / adjacent
        near = [s for s in syms if s['val'] and (lo-0x40) <= s['val'] <= (hi+0x40)]
        for s in near:
            print("     sym 0x%08X size=%-5d %-40s (info&0xF=%d shndx=%d)" % (s['val'], s['size'], s['name'], s['info']&0xF, s['shndx']))
        ov = [s for s in syms if s['size'] and s['val'] < hi and s['val']+s['size'] > lo]
        print("     symbols overlapping region: %d" % len(ov))
        for s in ov[:6]:
            print("        OVERLAP 0x%08X size=%d %s" % (s['val'], s['size'], s['name']))
        # which func range covers lo?
        cov = [r for r in fr if r[0] <= lo < r[1]]
        print("     FUNC range covering 0x%08X: %s" % (lo, ["0x%08X..0x%08X" % r for r in cov]))
        # following code
        print("     --- 6 instr before ---")
        for va in range(lo-24, lo, 4):
            print("       0x%08X  %08X  %s" % (va, e.word(va), dis(e.word(va), va)))
        print("     --- 6 instr after ---")
        for va in range(hi, min(hi+24, 0x5DED00), 4):
            print("       0x%08X  %08X  %s" % (va, e.word(va), dis(e.word(va), va)))
