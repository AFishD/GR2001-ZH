import zipfile, struct, os
p = r"work\builds\GR_OOMFIX\common\state_LAY_fix1_bytecount.p2s"
raw = open(p,'rb').read(64)
print("head:", raw[:16].hex(), raw[:4])
print("size:", os.path.getsize(p))
try:
    z = zipfile.ZipFile(p)
    for i in z.infolist():
        print("  %-28s comp=%d size=%-10d csize=%-10d crc=%08X" % (i.filename, i.compress_type, i.file_size, i.compress_size, i.CRC))
except Exception as e:
    print("not a zip:", e)
