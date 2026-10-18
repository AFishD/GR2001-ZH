import sys, struct
sys.path.insert(0, r"tools\rounds\oomfix\tools")
from oomfix_cave import read_elf
data, lba, size = read_elf(r"work\builds\GR_REBUILD\GR_REBUILD2400.iso")
e_shoff, = struct.unpack_from("<I", data, 0x20)
e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 0x2E)
print("shoff=0x%X shentsize=%d shnum=%d shstrndx=%d" % (e_shoff, e_shentsize, e_shnum, e_shstrndx))
shs=[struct.unpack_from("<10I", data, e_shoff+i*e_shentsize) for i in range(e_shnum)]
strtab = shs[e_shstrndx]
def nm(off):
    end = data.index(b"\0", strtab[4]+off)
    return data[strtab[4]+off:end].decode("latin-1")
tot=0
for i,sh in enumerate(shs):
    name,typ,flags,addr,off,sz,link,info,align,entsz = sh
    print("%2d %-22s type=%2d flags=0x%X addr=0x%08X off=0x%07X size=0x%07X" % (i, nm(name), typ, flags, addr, off, sz))
