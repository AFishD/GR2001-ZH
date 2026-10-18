import struct
S = open(r"work\builds\GR_OOMFIX\temp\state_LAY_eeram.bin",'rb').read()
for tag,p in (('p2 f43', r"work\builds\GR_OOMFIX\runs\p2_patched_state\win_f00000043_eeram.bin"),
              ('p2 f44', r"work\builds\GR_OOMFIX\runs\p2_patched_state\win_f00000044_eeram.bin"),
              ('u1 f46', r"work\builds\GR_OOMFIX\runs\u1_base_l1\win_f00000046_eeram.bin")):
    D = open(p,'rb').read()
    print("== 状态存档 vs %s" % tag)
    for lo,hi,why in ((0x0,0x400,'异常向量 0x0..0x400'),(0x400,0x1000,'0x400..0x1000'),
                      (0x1000,0x1400,'0x1000..0x1400'),(0x14000,0x16000,'内核异常表 0x14000..0x16000')):
        n = sum(1 for k in range(lo,hi) if S[k]!=D[k])
        first = next((k for k in range(lo,hi) if S[k]!=D[k]), None)
        print("   %-28s 差分 %5d B  首差 %s" % (why, n, 'None' if first is None else '0x%05X (%02X->%02X)'%(first,S[first],D[first])))
    # 0x15900 表逐字对照
    print("   0x15900 表:")
    for i in range(16):
        a = 0x15900+4*i
        s,d = struct.unpack_from('<I',S,a)[0], struct.unpack_from('<I',D,a)[0]
        if s != d:
            print("      +0x%02X  %08X -> %08X   %s" % (4*i, s, d, '★0x7E7E7E7E' if d==0x7E7E7E7E else ''))
