# -*- coding: utf-8 -*-
r"""zero_elfstr.py — 读 ELF 里与"纹理/pak 路径/字体资源名"有关的字符串常量（只读）

先按 ELF program header 建立 VA→文件偏移映射（不猜），再 dump 关心的串。
"""
import os
import struct
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
f = open(ISO, 'rb')
f.seek(0, 2)
ISO_SZ = f.tell()

# 找 ELF 头
ELF_OFF = None
for off in range(0x80000, 0xA0000, 0x800):
    f.seek(off)
    if f.read(4) == b'\x7fELF':
        ELF_OFF = off
        break
assert ELF_OFF is not None, 'ELF 头没找到'
print('[elf] ISO 偏移 0x%X' % ELF_OFF)
f.seek(ELF_OFF)
hdr = f.read(0x40)
e_phoff = struct.unpack_from('<I', hdr, 0x1C)[0]
e_phentsize = struct.unpack_from('<H', hdr, 0x2A)[0]
e_phnum = struct.unpack_from('<H', hdr, 0x2C)[0]
print('[elf] phoff=0x%X phentsize=%d phnum=%d' % (e_phoff, e_phentsize, e_phnum))
SEGS = []
for i in range(e_phnum):
    f.seek(ELF_OFF + e_phoff + i * e_phentsize)
    ph = f.read(e_phentsize)
    p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<IIIIII', ph, 0)
    if p_type == 1:
        SEGS.append((p_vaddr, p_offset, p_filesz, p_memsz))
        print('[elf] LOAD va=0x%08X off=0x%08X filesz=0x%X memsz=0x%X' % (p_vaddr, p_offset, p_filesz, p_memsz))


def va2iso(va):
    for v, o, fs, ms in SEGS:
        if v <= va < v + fs:
            return ELF_OFF + o + (va - v)
    return None


def read_va(va, n):
    o = va2iso(va)
    if o is None:
        return b''
    f.seek(o)
    return f.read(n)


def cstr(va, maxn=200):
    return read_va(va, maxn).split(b'\x00')[0].decode('latin-1')


for nm, va in [('kFontResource', 0x57AD70), ('0x57ABE0', 0x57ABE0), ('0x57AD60', 0x57AD60),
               ('pda_counterparts', 0x578650), ('pda2', 0x578D60),
               ('LoadingTexturePak base', 0x58C1A4), ('DAT_0058c1ef', 0x58C1EF)]:
    print('%-24s VA 0x%08X: %r' % (nm, va, cstr(va, 200)))

print()
print('=== 全 ELF 扫描 .rsb / .pak / .res / host0: 串 ===')
# 扫描: 主段
import re
buf = read_va(SEGS[0][0], SEGS[0][2])
pat = re.compile(rb'[ -~]{4,120}')
found = {}
for m in pat.finditer(buf):
    s = m.group(0)
    low = s.lower()
    if low.endswith(b'.rsb') or low.endswith(b'.pak') or low.endswith(b'.res') or b'host0:' in low \
            or b'.img' in low or b'uitexture' in low:
        va = SEGS[0][0] + m.start()
        found[va] = s.decode('latin-1')
for va in sorted(found):
    s = found[va]
    if any(k in s.lower() for k in ('font', 'pak', 'uitexture', 'img', 'host0', 'rsb', 'res;')):
        print('  0x%08X  %r' % (va, s))
f.close()
