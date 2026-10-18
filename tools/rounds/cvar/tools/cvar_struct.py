# -*- coding: utf-8 -*-
r"""cvar_struct.py — 解析本盘 IMG 容器结构 + COMMON.PAK + 字库容器 + FONT.RES 记录

用法:
    python cvar_struct.py --iso <iso> [--only MENU.IMG] [--dump-entries] [--js <out.json>]

只读。输出: IMG 头 / 名字表 / 12×u32 条目表 / 每个条目的 ISO 绝对偏移;
        COMMON.PAK 头与其中条目; 字库容器记录 (w,h,px_size...)。
"""
import argparse
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
SEC = 2048
TAB_OFF, TAB_STEP = 0x830, 48
IMG_LBA = {'MENU.IMG': 776286, 'GR.IMG': 19175}


def parse_pvd(d):
    pvd = 16 * SEC
    assert d[pvd + 1:pvd + 6] == b'CD001'
    return {
        'vol_space': struct.unpack_from('<I', d, pvd + 80)[0],
        'root_lba': struct.unpack_from('<I', d, pvd + 158)[0],
        'root_size': struct.unpack_from('<I', d, pvd + 166)[0],
    }


def read_dir(d, lba, size):
    out = []
    data = d[lba * SEC:lba * SEC + size]
    i = 0
    while i < len(data):
        L = data[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            if i >= len(data):
                break
            continue
        if i + L > len(data) or L < 34:
            break
        rec = data[i:i + L]
        ext = struct.unpack_from('<I', rec, 2)[0]
        sz = struct.unpack_from('<I', rec, 10)[0]
        out.append((rec[33:33 + rec[32]], ext, sz, rec[25], lba * SEC + i, L))
        i += L
    return out


def walk(d, lba, size, prefix, acc):
    for nm, ext, sz, fl, absoff, L in read_dir(d, lba, size):
        if nm in (b'\x00', b'\x01'):
            continue
        name = nm.decode('latin-1')
        p = (prefix + '/' + name) if prefix else name
        acc.append({'path': p, 'lba': ext, 'size': sz, 'is_dir': bool(fl & 2),
                    'dirrec_off': absoff, 'dirrec_len': L})
        if fl & 2:
            walk(d, ext, sz, p, acc)
    return acc


def img_header(d, lba):
    b = lba * SEC
    return {
        'lba': lba,
        'iso_off': b,
        'f00': struct.unpack_from('<I', d, b + 0x00)[0],
        'f04_nend': struct.unpack_from('<I', d, b + 0x04)[0],
        'f08': struct.unpack_from('<I', d, b + 0x08)[0],
        'f0c': struct.unpack_from('<I', d, b + 0x0C)[0],
        'f10_noff': struct.unpack_from('<I', d, b + 0x10)[0],
        'f14': struct.unpack_from('<I', d, b + 0x14)[0],
        'f18': struct.unpack_from('<I', d, b + 0x18)[0],
        'f1c': struct.unpack_from('<I', d, b + 0x1C)[0],
    }


def img_entries(d, lba):
    b = lba * SEC
    noff = struct.unpack_from('<I', d, b + 0x10)[0]
    nend = struct.unpack_from('<I', d, b + 0x04)[0]
    names = [x.decode('latin-1') for x in d[b + noff:b + nend].split(b'\x00') if x]
    ents = []
    for i, nm in enumerate(names):
        f = list(struct.unpack_from('<12I', d, b + TAB_OFF + TAB_STEP * i))
        ents.append({'idx': i, 'name': nm, 'f': f,
                     'tab_iso': b + TAB_OFF + TAB_STEP * i})
    return ents


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--js', default=None)
    ap.add_argument('--dump-entries', action='store_true')
    x = ap.parse_args()
    d = open(x.iso, 'rb').read()
    print('ISO %s  %d B' % (x.iso, len(d)))
    pvd = parse_pvd(d)
    print('PVD %s' % pvd)
    files = walk(d, pvd['root_lba'], pvd['root_size'], '', [])
    res = {'iso': x.iso, 'size': len(d), 'pvd': pvd, 'files': files, 'imgs': {}}
    print('\n== ISO9660 文件 (%d) ==' % len(files))
    for f in files:
        print('  %-24s LBA=%-8d size=%-10d iso=0x%09X..0x%09X dirrec@0x%09X len=%d'
              % (f['path'], f['lba'], f['size'], f['lba'] * SEC,
                 f['lba'] * SEC + f['size'], f['dirrec_off'], f['dirrec_len']))

    for nm in ('MENU.IMG', 'GR.IMG'):
        lba = IMG_LBA[nm]
        h = img_header(d, lba)
        ents = img_entries(d, lba)
        res['imgs'][nm] = {'header': h, 'entries': ents}
        print('\n== %s @LBA %d iso=0x%X ==' % (nm, lba, lba * SEC))
        print('   hdr ' + ' '.join('%s=0x%X(%d)' % (k, v, v) for k, v in h.items()
                                   if k not in ('lba', 'iso_off')))
        print('   条目 %d 个' % len(ents))
        if x.dump_entries:
            for e in ents:
                f = e['f']
                print('    [%3d] %-20s ' % (e['idx'], e['name'])
                      + ' '.join('%02d:%08X' % (i, v) for i, v in enumerate(f)))
                if f[8]:
                    print('          off=0x%X(%d) stored=0x%X(%d) real=0x%X(%d) 文件内 0x%X..0x%X'
                          % (f[8], f[8], f[6], f[6], f[7], f[7],
                             lba * SEC + f[8], lba * SEC + f[8] + max(f[6], f[7])))
    if x.js:
        with open(x.js, 'w', encoding='utf-8', newline='\n') as fo:
            json.dump(res, fo, indent=1)
        print('\n→ %s' % x.js)
    return 0


if __name__ == '__main__':
    sys.exit(main())
