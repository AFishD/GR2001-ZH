# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/slus_scan/elf_info.py (逐字复制)。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys
p = os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13')
d = open(p,'rb').read(4096)
assert d[:4] == b'\x7fELF', d[:4]
print("class:", d[4], "endian:", d[5], "(1=LSB)")
etype, machine, ver, entry, phoff, shoff, flags, ehsize, phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from('<HHIIIIIHHHHHH', d, 16)
print("type=%d machine=%d entry=0x%08X phoff=0x%X shoff=0x%X flags=0x%08X" % (etype, machine, entry, phoff, shoff, flags))
print("phnum=%d shnum=%d" % (phnum, shnum))
import os
size = os.path.getsize(p)
print("file size:", size, hex(size))
f = open(p,'rb')
f.seek(shoff)
shs = []
for i in range(shnum):
    b = f.read(shentsize)
    name,typ,flags,addr,off,size2,link,info,align,entsize = struct.unpack('<10I', b)
    shs.append((name,typ,flags,addr,off,size2))
# shstrtab
strtab_off = shs[shstrndx][4]
f.seek(strtab_off)
strtab = f.read(shs[shstrndx][5])
def nm(x):
    e = strtab.index(b'\0', x)
    return strtab[x:e].decode('latin1')
for i,s in enumerate(shs):
    print("[%2d] %-18s typ=%2d addr=0x%08X off=0x%08X size=0x%X" % (i, nm(s[0]), s[1], s[3], s[4], s[5]))
