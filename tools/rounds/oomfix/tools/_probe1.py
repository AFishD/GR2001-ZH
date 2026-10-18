import sys, struct, os
sys.path.insert(0, r"tools\rounds\oomfix\tools")
from oomfix_cave import read_elf, Elf
data, lba, size = read_elf(r"work\builds\GR_REBUILD\GR_REBUILD2400.iso")
e = Elf(data)
for va in (0x565670, 0x565730, 0x5657C8, 0x565900, 0x565930, 0x565A00, 0x565A48, 0x565B00,
           0x416ED0, 0x416F40, 0x417050, 0x417150, 0x4176A0, 0x565600, 0x565500, 0x565400):
    print("0x%08X = 0x%08X" % (va, e.word(va)))
print("iso_off(0x565670) = 0x%X" % (e.va2off(0x565670)))
print("iso_off(0x539174) = 0x%X" % (e.va2off(0x539174)))
print("symbols at 0x565670ff:", [s for s in e.syms() if 0x565600 <= s['val'] < 0x565B00][:8])
