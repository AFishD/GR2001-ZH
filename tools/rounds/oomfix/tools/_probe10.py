import struct
d = open(r"work\builds\GR_OOMFIX\temp\state_LAY_eeram.bin",'rb').read()
print("state RAM size =", len(d))
for va,name in ((0x53916C,'jal malloc'),(0x539174,'F1 site'),(0x539178,'delay slot'),(0x550048,'cave'),(0x51BE10,'caller'),(0x1300,'0x1300')):
    print("  0x%08X %-12s = %08X  %s" % (va, name, struct.unpack_from('<I', d, va)[0], d[va:va+8].hex()))
