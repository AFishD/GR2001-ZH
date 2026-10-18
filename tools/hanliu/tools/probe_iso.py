# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/probe_iso.py (逐字复制 (ELF@LBA295+MENU@LBA776286 组装))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""probe_iso.py — 参数化实验盘组装: 原盘 + 指定 ELF + 指定 MENU → ISO (原位替换, 尺寸不变)
用法: probe_iso.py <ELF> <MENU> <ISO_OUT>
"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import os, struct, sys

ISO_SRC = os.path.join(REPO_ROOT, 'Tom Clancy\'s Ghost Recon (USA).iso')
MENU_LBA = 776286
SECTOR = 2048
ELF_LBA = 295  # 与 db1_iso.py 实测一致; 下方仍动态校验

def find_file(iso, wanted):
    with open(iso, 'rb') as f:
        pvd = None
        for sector in range(16, 32):
            f.seek(sector * SECTOR)
            hdr = f.read(8)
            if hdr[0:1] == b'\x01' and hdr[1:6] == b'CD001':
                pvd = sector; break
        assert pvd is not None
        f.seek(pvd * SECTOR + 156)
        root = f.read(34)
        def walk(lba, size):
            f.seek(lba * SECTOR); data = f.read(size); p = 0
            while p < len(data):
                ln = data[p]
                if ln == 0:
                    p = (p // SECTOR + 1) * SECTOR; continue
                ext_lba, _, fsize = struct.unpack_from('<II I', data, p + 2)
                flags = data[p + 25]; nl = data[p + 32]
                name = data[p + 33:p + 33 + nl]
                name = name.decode('latin-1').split(';')[0] if nl > 1 else {b'\x00': '.', b'\x01': '..'}.get(bytes(name), '?')
                p += ln
                if name in ('.', '..'):
                    continue
                if flags & 2:
                    yield from walk(ext_lba, fsize)
                else:
                    yield name.upper(), ext_lba, fsize
        for nm, lba, size in walk(struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0]):
            if nm == wanted.upper():
                return lba, size
    return None

def main():
    elf_path, menu_path, iso_out = sys.argv[1], sys.argv[2], sys.argv[3]
    hit = find_file(ISO_SRC, 'SLUS_206.13')
    elf_lba, elf_size = hit
    assert elf_lba == ELF_LBA, (elf_lba, ELF_LBA)
    elf_patched = open(elf_path, 'rb').read()
    assert len(elf_patched) == elf_size, 'ELF 尺寸不符'
    menu = open(menu_path, 'rb').read()
    assert len(menu) == 58300882, len(menu)
    src_size = os.path.getsize(ISO_SRC)
    with open(ISO_SRC, 'rb') as src, open(iso_out, 'wb') as dst:
        elf_off = elf_lba * SECTOR
        menu_off = MENU_LBA * SECTOR
        chunk = 1 << 24
        def cp(a, b):
            src.seek(a); pos = a
            while pos < b:
                n = min(chunk, b - pos)
                dst.write(src.read(n)); pos += n
        cp(0, elf_off)
        dst.write(elf_patched)
        cp(elf_off + len(elf_patched), menu_off)
        dst.write(menu)
        cp(menu_off + len(menu), src_size)
    with open(iso_out, 'rb') as f:
        f.seek(elf_lba * SECTOR); assert f.read(elf_size) == elf_patched
        f.seek(menu_off); assert f.read(len(menu)) == menu
    assert os.path.getsize(iso_out) == src_size
    print('OK', iso_out, 'ELF=', os.path.basename(elf_path), 'MENU=', os.path.basename(menu_path))

if __name__ == '__main__':
    main()
