# -*- coding: utf-8 -*-
# [hanliu 收编] 原件: C:/gr_build/tmp/dbcs/verify_iso.py (逐字复制 (ISO 内 ELF/MENU 比对))。原件保留于原处未动。
# 工具链总览见 hanliu/README.md 与 hanliu/tools/__init__.py。
"""verify_iso.py — 核对 GR_DB1.iso / GR_DB2.iso 内 ELF 与 MENU 是否与 tmp\dbcs 产物一致"""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

import struct, sys

SECTOR = 2048
MENU_LBA = 776286

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
                name = name.decode('latin-1').split(';')[0] if nl > 1 else {b'\x00':'.',b'\x01':'..'}.get(bytes(name),'?')
                p += ln
                if name in ('.', '..'): continue
                if flags & 2:
                    yield from walk(ext_lba, fsize)
                else:
                    yield name.upper(), ext_lba, fsize
        root_lba = struct.unpack_from('<I', root, 2)[0]
        root_sz = struct.unpack_from('<I', root, 10)[0]
        for nm, lba, size in walk(root_lba, root_sz):
            if nm == wanted.upper():
                return lba, size
    return None

def check(iso_path, elf_path, menu_path):
    print('===', iso_path)
    hit = find_file(iso_path, 'SLUS_206.13')
    assert hit, '未找到 SLUS_206.13'
    elf_lba, elf_size = hit
    elf_iso = open(iso_path, 'rb').read()[elf_lba*SECTOR:elf_lba*SECTOR+elf_size]
    elf_ref = open(elf_path, 'rb').read()
    menu_iso = open(iso_path, 'rb').read()[MENU_LBA*SECTOR:MENU_LBA*SECTOR+len(open(menu_path,'rb').read())]
    menu_ref = open(menu_path, 'rb').read()
    print('ELF @LBA %d size %d: iso==%s -> %s' % (elf_lba, elf_size, elf_path.split("\\")[-1], elf_iso == elf_ref))
    print('MENU @LBA %d len %d: iso==%s -> %s' % (MENU_LBA, len(menu_ref), menu_path.split("\\")[-1], menu_iso == menu_ref))
    # 与原盘 ELF 差异确认非零
    orig = open(os.path.join(REPO_ROOT, 'build', 'bases', 'slus_out', 'SLUS_206.13'), 'rb').read()
    nd = sum(1 for a,b in zip(elf_iso, orig) if a != b)
    print('ELF vs 原件差异字节: %d' % nd)
    return elf_iso == elf_ref and menu_iso == menu_ref and nd > 0

ok1 = check(os.path.join(REPO_ROOT, 'build', 'iso', 'GR_DB1.iso'), os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'SLUS_db1.elf'), os.path.join(REPO_ROOT, 'work', 'tmp', 'dbcs', 'MENU_db1.img'))
print('DB1 对应关系:', 'PASS' if ok1 else 'FAIL')
