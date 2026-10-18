import struct, sys
def find(path, val, limit=25):
    d = open(path,'rb').read()
    b = struct.pack('<I', val)
    hits=[]; i=0
    while True:
        j = d.find(b, i)
        if j < 0 or len(hits) >= 2000: break
        hits.append(j); i = j+1
    print("%s : %d 处 0x%08X" % (path.split('\\')[-1], len(hits), val))
    print("   ", ["0x%08X" % h for h in hits[:limit]])
    return hits
find(r"work\builds\GR_OOMFIX\runs\p2_patched_state\win_f00000044_eeram.bin", 0x7E7E7E7E)
find(r"work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000044_eeram.bin", 0x7E7E7E7E)
find(r"work\builds\GR_OOMFIX\temp\state_LAY_eeram.bin", 0x7E7E7E7E)
# 看看 s1 结构 0x0129F320 与 0x01261AB0 附近
d = open(r"work\builds\GR_OOMFIX\runs\p2_patched_state\win_f00000044_eeram.bin",'rb').read()
for base in (0x0129F320, 0x01261AB0):
    print("s1=0x%08X:" % base)
    for off in range(0, 0x60, 0x10):
        print("   +0x%02X %s" % (off, d[base+off:base+off+16].hex()))
