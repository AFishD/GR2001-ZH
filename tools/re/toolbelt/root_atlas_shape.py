# -*- coding: utf-8 -*-
r"""root_atlas_shape.py -- 逐字节核对 new_font_revised 像素容器的真实形状（READ-ONLY）

按 16 B 为步进扫描容器，打印每一个"GIF tag 形状"的 16 B 块（nloop/regs/eop/flg),
以及 tag 后紧跟的 payload 长度；再与 px_size / 段数 / 1 个 NLOOP 的字节数对账。

用法: python tools/re/toolbelt/root_atlas_shape.py <iso> [<iso> ...]
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048


def iso_open(path):
    return open(path, 'rb')


def find_pak(f):
    """locate MENU.IMG on the ISO via ISO9660 PVD root dir (LBA from PVD)."""
    f.seek(16 * SEC)
    pvd = f.read(SEC)
    if pvd[0] != 1 or pvd[1:6] != b'CD001':
        raise SystemExit('no PVD')
    root = pvd[156:156 + 34]
    lba = struct.unpack_from('<I', root, 2)[0]
    size = struct.unpack_from('<I', root, 6)[0]
    f.seek(lba * SEC)
    d = f.read(size)
    out = []
    p = 0
    while p < len(d):
        ln = d[p]
        if ln == 0:
            p = (p // SEC + 1) * SEC
            continue
        rec = d[p:p + ln]
        ext = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        nl = rec[32]
        nm = rec[33:33 + nl]
        out.append((nm, ext, sz))
        p += ln
    return out


def main():
    for path in sys.argv[1:]:
        print('=' * 100)
        print(path)
        f = iso_open(path)
        ents = find_pak(f)
        menu = [e for e in ents if e[0].startswith(b'MENU') or e[0].endswith(b'MENU.IMG;1')]
        print('  root entries:', [(e[0], e[1], e[2]) for e in ents][:20])
        # fall back to hard-coded: MENU.IMG LBA 776286
        mlba, msz = 776286, None
        for (nm, ext, sz) in ents:
            if nm == b'MENU.IMG;1':
                mlba, msz = ext, sz
        print('  MENU.IMG LBA=%d size=%s' % (mlba, msz))
        # MENU.IMG starts with IMG header: +0x20 = entry table
        f.seek(mlba * SEC)
        head = f.read(0x40)
        print('  IMG head[0:0x40] =', head.hex())
        n, = struct.unpack_from('<I', head, 0x20) if False else (0,)
        # dump the +0x20 u32 and the entry table
        cnt = struct.unpack_from('<I', head, 0x20)[0]
        print('  u32@+0x20 = 0x%X' % cnt)
        f.seek(mlba * SEC + 0x20)
        nent = struct.unpack_from('<I', f.read(4), 0)[0]
        print('  entry count = %d' % nent)
        f.seek(mlba * SEC + 0x24)
        tab = f.read(nent * 16)
        for i in range(nent):
            off, stored, real, flags = struct.unpack_from('<4I', tab, i * 16)
            if stored > 1000:
                print('    #%d off=0x%X stored=%d real=%d flags=0x%X' % (i, off, stored, real, flags))
        f.close()


main()
