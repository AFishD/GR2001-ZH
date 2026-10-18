# r74_elf_layout.py - dump ELF program/section headers of the PS2 ELF and locate
# where file-offset/VA 0x25E86C lives, plus decode the bytes there.
import struct, sys, io

ELF = r"work/builds/GR_ZH98/temp/r72/SLUS_206.13.elf"

data = open(ELF, "rb").read()
print("file size =", len(data))
assert data[:4] == b"\x7fELF", "not ELF"
ei_class = data[4]
print("EI_CLASS =", ei_class, "(1=32bit,2=64bit)")
print("EI_DATA  =", data[5], "(1=LE)")

# ELF32 header
(e_type, e_machine, e_version, e_entry, e_phoff, e_shoff, e_flags,
 e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx) = struct.unpack_from(
    "<HHIIIIIHHHHHH", data, 16)
print(f"type={e_type:#x} machine={e_machine:#x} entry={e_entry:#010x} flags={e_flags:#x}")
print(f"phoff={e_phoff} phnum={e_phnum} phentsize={e_phentsize}")
print(f"shoff={e_shoff:#x} shnum={e_shnum} shentsize={e_shentsize} shstrndx={e_shstrndx}")

print("\n=== PROGRAM HEADERS ===")
phdrs = []
for i in range(e_phnum):
    off = e_phoff + i * e_phentsize
    p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align = \
        struct.unpack_from("<IIIIIIII", data, off)
    phdrs.append((p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align))
    print(f"  [{i}] type={p_type:#x} off={p_offset:#010x} vaddr={p_vaddr:#010x} "
          f"paddr={p_paddr:#010x} filesz={p_filesz:#010x} memsz={p_memsz:#010x} flags={p_flags}")

print("\n=== SECTIONS ===")
# read section header string table name
shdrs = []
for i in range(e_shnum):
    off = e_shoff + i * e_shentsize
    (sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link,
     sh_info, sh_addralign, sh_entsize) = struct.unpack_from("<IIIIIIIIII", data, off)
    shdrs.append((sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size))

if e_shstrndx < e_shnum:
    strtab_off = shdrs[e_shstrndx][4]
    def nm(x):
        e = data.index(b"\0", strtab_off + x)
        return data[strtab_off + x:e].decode("latin1")
    for i, s in enumerate(shdrs):
        print(f"  [{i:2d}] {nm(s[0]):<22} type={s[1]:#04x} flags={s[2]:#x} "
              f"addr={s[3]:#010x} off={s[4]:#010x} size={s[5]:#010x}")
else:
    print("  (no section name table, shstrndx=%d)" % e_shstrndx)

print("\n=== who maps VA 0x25E86C ? ===")
TARGET = 0x25E86C
found = False
for i, (p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align) in enumerate(phdrs):
    if p_type == 1 and p_vaddr <= TARGET < p_vaddr + p_memsz:
        fo = p_offset + (TARGET - p_vaddr)
        print(f"  PHDR[{i}] maps it. VA {p_vaddr:#x}+{p_memsz:#x} filesz={p_filesz:#x} "
              f"-> file offset {fo:#x}")
        found = True
        print("  bytes:", data[fo:fo+64].hex(" "))
        break
if not found:
    print("  !! no PT_LOAD maps 0x25E86C")

print("\n=== raw bytes at several VAs (using PT_LOAD mapping) ===")
def va2off(va):
    for (p_type, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_flags, p_align) in phdrs:
        if p_type == 1 and p_vaddr <= va < p_vaddr + p_filesz:
            return p_offset + (va - p_vaddr)
    return None

for va in (0x25E86C, 0x101D10, 0x101DD8, 0x101E6C, 0x25E730):
    o = va2off(va)
    print(f"  VA {va:#010x} -> off {o if o is None else hex(o)}")
    if o is not None:
        print("      ", data[o:o+48].hex(" "))

# is 0x25E86C inside a code region at all?  print a window
print("\n=== window around 0x25E800 (VA), 256 bytes ===")
o = va2off(0x25E800)
if o:
    chunk = data[o:o+256]
    for r in range(0, 256, 16):
        va = 0x25E800 + r
        row = chunk[r:r+16]
        words = " ".join(f"{struct.unpack_from('<I', row, k)[0]:08x}" for k in range(0, 16, 4))
        print(f"  {va:08x}  {words}")
