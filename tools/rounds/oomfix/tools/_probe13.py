import sys, struct
sys.path.insert(0, r"tools\re\toolbelt")
from cave_dis import dis
d = open(r"work\builds\GR_OOMFIX\temp\state_LAY_eeram.bin",'rb').read()
print("=== 状态存档 eeMemory 0x000000..0x000300（异常向量区）===")
for va in range(0x0, 0x300, 4):
    w = struct.unpack_from('<I', d, va)[0]
    print("  %08x  %08x  %s" % (va, w, dis(w, va)))
