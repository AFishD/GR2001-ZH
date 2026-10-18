import struct, hashlib
p = r"work\builds\GR_OOMFIX\OOMFIX_lay1.iso"
f = open(p,'rb')
for (off,name) in ((0x4CC9F4,'F1 (VA 0x539174)'),(0x4E38C8,'cave (VA 0x550048)'),(0x4E38F8,'cave fail (VA 0x550060)')):
    f.seek(off); b = f.read(16)
    print("ISO 0x%07X %-22s %s  word=%08X" % (off, name, b.hex(), struct.unpack_from('<I', b, 0)[0]))
f.close()
# 也顺手核一下 LAY 基底同一个偏移
f = open(r"work\builds\GR_LAYOUT\LAY_fix1_bytecount.iso",'rb')
for (off,name) in ((0x4CC9F4,'F1'),(0x4E38C8,'cave')):
    f.seek(off); b = f.read(16)
    print("LAY 0x%07X %-6s %s" % (off, name, b.hex()))
f.close()
