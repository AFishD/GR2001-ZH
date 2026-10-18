# -*- coding: utf-8 -*-
r"""root_ram_find.py -- 在 EE RAM 快照里定位图集容器/像素缓冲的真实形态（READ-ONLY）

用法:
  python tools/re/toolbelt/root_ram_find.py <eeram.bin> <eeram_of_container.bin> [--seg16]
说明:
  · 从「参考 ISO」里取 new_font_revised 容器前 0x100 / 0x8030+0x100 字节作签名
  · 在 RAM 快照里找签名命中，打印命中偏移，并把命中点前后按 16 B 块列出
"""
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
MENU_LBA = 776286


def container(reference_iso, pak_name='new_font_revised'):
    with open(reference_iso, 'rb') as f:
        f.seek(MENU_LBA * SEC)
        head = f.read(0x30)
        noff = struct.unpack_from('<I', head, 0x10)[0]
        nend = struct.unpack_from('<I', head, 4)[0]
        f.seek(MENU_LBA * SEC)
        mm = f.read(max(nend, 0x830 + 48 * 700))
        names = [x.decode('latin-1') for x in mm[noff:nend].split(b'\x00') if x]
        ent = None
        for i, nm in enumerate(names):
            r = struct.unpack_from('<12I', mm, 0x830 + 48 * i)
            if nm == 'COMMON.PAK':
                ent = (r[8], r[6])
        off, stored = ent
        f.seek(MENU_LBA * SEC + off)
        pak = f.read(stored)
    p = 0
    while p + 8 <= len(pak):
        mode, nl = struct.unpack_from('<II', pak, p)
        nm = pak[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
        r = p + 8 + nl
        if mode == 0:
            psm, w, h, clut_size = struct.unpack_from('<4I', pak, r)
            q = r + 16 + clut_size
            px_size, = struct.unpack_from('<I', pak, q)
            q += 4
            if nm == pak_name:
                return dict(w=w, h=h, psm=psm, px_size=px_size, px=pak[q:q + px_size])
            p = q + px_size
        else:
            break
    raise SystemExit('not found')


def main():
    REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))

    def rp(p):
        return p if os.path.isabs(p) else os.path.join(REPO, p)

    ram_path = rp(sys.argv[1])
    ref = rp(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(REPO, 'work', 'builds', 'GR_ZH123', 'GR_ZH123.iso')
    c = container(ref)
    print('容器 w=%d h=%d psm=0x%X px_size=0x%X' % (c['w'], c['h'], c['psm'], c['px_size']))
    px = c['px']
    print('前 0x30: %s' % px[:0x30].hex(' '))
    print('seg1 @0x8030 前 0x30: %s' % px[0x8030:0x8030 + 0x30].hex(' '))
    sig = px[0x00:0x30]                 # 第 0 段的 48 B GIF 头（PT + TRXPOS + IMAGE tag）
    sig2 = px[0x8030:0x8030 + 0x30]     # 第 1 段的头（TRXPOS 的 SSAY=0x40）
    d = open(ram_path, 'rb').read()
    print('RAM %s = %d B' % (ram_path, len(d)))
    for label, s in (('seg0 头 48B', sig), ('seg1 头 48B', sig2)):
        i = d.find(s)
        n = 0
        while i >= 0 and n < 12:
            print('  %-12s 命中 @0x%08X' % (label, i))
            # 打印命中点前 0x40 / 后 0x40
            print('        -0x40: %s' % d[max(0, i - 0x40):i].hex(' '))
            print('        +0x00: %s' % d[i:i + 0x40].hex(' '))
            i = d.find(s, i + 1)
            n += 1
        if n == 0:
            print('  %-12s 未命中' % label)
    # 找 0x00111111 长游程（调色板索引 1 填充）
    best = (0, 0)
    i = 0
    while i < len(d):
        if d[i] == 0x11:
            j = i
            while j < len(d) and d[j] == 0x11:
                j += 1
            if j - i > best[1]:
                best = (i, j - i)
            i = j
        else:
            i += 1
    print('  最长 0x11 游程 @0x%X 长 %d B (0x%X)' % (best[0], best[1], best[1]))


main()
