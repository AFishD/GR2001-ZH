#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""make_iso.py — 一键组装成品 ISO (基底原盘 + 补丁 MENU + 可选补丁 ELF → 原尺寸 ISO)

原位替换两处 (与盘上布局逐字节核实过):
  ELF  SLUS_206.13 @ LBA 295    (可选, DBCS 补丁 ELF 如 SLUS_P_U.elf; 尺寸必须与原件一致)
  MENU MENU.IMG      @ LBA 776286 (58,300,882B)

内部逻辑 = probe_iso.py / splice_iso.py (均经 GR_DB1..GR_ZH7 全系列实测)。
写完自动回读比对 + 总尺寸断言 = 原盘尺寸。

用法:
  python make_iso.py --base-iso <原盘iso> --menu <补丁MENU.img> --out <成品iso>
  python make_iso.py --base-iso <原盘iso> --menu <MENU.img> --elf <SLUS_P_U.elf> --out <iso>
只读基底, 输出写 --out; 基底与输出同路径时拒绝 (防覆盖原盘)。
"""
import argparse
import os
import struct
import sys

SECTOR = 2048
MENU_LBA = 776286
ELF_LBA = 295
MENU_SIZE = 58300882


def die(msg):
    raise SystemExit('[make_iso] FAIL: ' + msg)


def find_file_lba(iso_path, wanted):
    """ISO9660 目录树查找文件 → (lba, size)。逻辑 = iso_tool/probe_iso。"""
    with open(iso_path, 'rb') as f:
        pvd = None
        for sector in range(16, 32):
            f.seek(sector * SECTOR)
            hdr = f.read(8)
            if hdr[0:1] == b'\x01' and hdr[1:6] == b'CD001':
                pvd = sector
                break
        if pvd is None:
            die('未找到 ISO9660 主卷描述符')
        f.seek(pvd * SECTOR + 156)
        root = f.read(34)

        def walk(lba, size):
            f.seek(lba * SECTOR)
            data = f.read(size)
            p = 0
            while p < len(data):
                ln = data[p]
                if ln == 0:
                    p = (p // SECTOR + 1) * SECTOR
                    continue
                ext_lba, _be, fsize = struct.unpack_from('<III', data, p + 2)
                flags = data[p + 25]
                nl = data[p + 32]
                name = data[p + 33:p + 33 + nl]
                name = name.decode('latin-1').split(';')[0] if nl > 1 else '?'
                p += ln
                if name in ('.', '..'):
                    continue
                if flags & 2:
                    yield from walk(ext_lba, fsize)
                else:
                    yield name.upper(), ext_lba, fsize
        for nm, lba, size in walk(struct.unpack_from('<I', root, 2)[0],
                                  struct.unpack_from('<I', root, 10)[0]):
            if nm == wanted.upper():
                return lba, size
    return None


def main():
    ap = argparse.ArgumentParser(description='成品 ISO 一键组装')
    ap.add_argument('--base-iso', required=True, help='基底原盘 ISO (只读)')
    ap.add_argument('--menu', required=True, help='补丁 MENU.IMG (58,300,882B)')
    ap.add_argument('--elf', help='补丁 ELF (可选, DBCS 盘需 SLUS_P_U)')
    ap.add_argument('--out', required=True, help='输出 ISO')
    a = ap.parse_args()
    if os.path.abspath(a.base_iso) == os.path.abspath(a.out):
        die('输出与基底同路径 — 拒绝覆盖原盘')
    menu = open(a.menu, 'rb').read()
    if len(menu) != MENU_SIZE:
        die('MENU 尺寸 %d != %d (必须原尺寸, 布局条目不得重排)' % (len(menu), MENU_SIZE))
    elf = open(a.elf, 'rb').read() if a.elf else None

    hit = find_file_lba(a.base_iso, 'SLUS_206.13')
    if not hit:
        die('ISO 内无 SLUS_206.13')
    elf_lba, elf_size = hit
    src_size = os.path.getsize(a.base_iso)
    if elf is not None:
        if len(elf) != elf_size:
            die('ELF 尺寸 %d != 盘上 %d' % (len(elf), elf_size))
        if elf_lba != ELF_LBA:
            print('  提示: 盘上 ELF LBA=%d (文档基准 %d)' % (elf_lba, ELF_LBA))

    menu_off = MENU_LBA * SECTOR
    elf_off = elf_lba * SECTOR
    with open(a.base_iso, 'rb') as src, open(a.out, 'wb') as dst:
        chunk = 1 << 24

        def cp(a0, b0):
            src.seek(a0)
            pos = a0
            while pos < b0:
                n = min(chunk, b0 - pos)
                dst.write(src.read(n))
                pos += n
        if elf is not None:
            cp(0, elf_off)
            dst.write(elf)
            cp(elf_off + len(elf), menu_off)
        else:
            cp(0, menu_off)
        dst.write(menu)
        cp(menu_off + len(menu), src_size)

    # 回读自检
    with open(a.out, 'rb') as f:
        f.seek(menu_off)
        if f.read(len(menu)) != menu:
            die('回读 MENU 不一致')
        if elf is not None:
            f.seek(elf_off)
            if f.read(len(elf)) != elf:
                die('回读 ELF 不一致')
    if os.path.getsize(a.out) != src_size:
        die('输出尺寸 %d != 原盘 %d' % (os.path.getsize(a.out), src_size))
    print('[make_iso] OK %s' % a.out)
    print('  MENU %s @LBA %d' % (os.path.basename(a.menu), MENU_LBA))
    if elf is not None:
        print('  ELF  %s @LBA %d' % (os.path.basename(a.elf), elf_lba))
    print('  尺寸 = 原盘 %d 字节, 回读比对 PASS' % src_size)
    return 0


if __name__ == '__main__':
    sys.exit(main())
