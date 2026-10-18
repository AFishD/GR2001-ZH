import struct
def dump(path, tag):
    d = open(path,'rb').read()
    print("== %s" % tag)
    for base,name in ((0x15900,'0x80015900 异常分派表（0x180 用）'),(0x15940,'0x80015940（0x200 用）'),(0x15500,'0x80015500（0x2F0 用）')):
        words = [struct.unpack_from('<I', d, base+4*i)[0] for i in range(16)]
        print("   %s:" % name)
        for i,w in enumerate(words):
            mark = '   <== 0x7E7E7E7E!' if w == 0x7E7E7E7E else ''
            print("      +0x%02X  %08X%s" % (4*i, w, mark))
for p,t in ((r"work\builds\GR_OOMFIX\temp\state_LAY_eeram.bin",'状态存档（崩前）'),
            (r"work\builds\GR_OOMFIX\runs\p2_patched_state\win_f00000043_eeram.bin",'p2 f43'),
            (r"work\builds\GR_OOMFIX\runs\p2_patched_state\win_f00000044_eeram.bin",'p2 f44')):
    dump(p,t)
