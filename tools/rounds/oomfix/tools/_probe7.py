import sys, struct
def show(path, tag):
    d = open(path,'rb').read()
    print("== %s (%d B)" % (tag, len(d)))
    for va,name in ((0x539174,'F1 site'),(0x539178,'delay slot'),(0x550048,'cave'),(0x550060,'cave .fail')):
        print("   0x%08X %-12s = %08X   bytes %s" % (va, name, struct.unpack_from('<I', d, va)[0], d[va:va+4].hex()))
import glob, os
run=r"work\builds\GR_OOMFIX\runs"
for f in sorted(glob.glob(os.path.join(run, "p1_patched_l1", "win_f*_eeram.bin"))):
    show(f, os.path.basename(f))
for f in sorted(glob.glob(os.path.join(run, "u1_base_l1", "win_f*_eeram.bin"))):
    show(f, os.path.basename(f))
