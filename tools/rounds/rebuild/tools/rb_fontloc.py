# -*- coding: utf-8 -*-
r"""rb_fontloc.py -- 只读：定位 FONT.RES / COMMON.PAK(new_font_revised) 在 MENU.IMG 内的
ISO 字节范围 / LBA，并核对哪些块的扇区落在幸存的 cdvd-dump 里（决定字形与记录表能否取回）。

用法: python rb_fontloc.py [--iso <盘>] [--out <txt>]
"""
import argparse
import glob
import io
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

SEC = 2048
DUMPDIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'cdvd-dump')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def load_idx(path):
    n = os.path.getsize(path)
    with open(path, 'rb') as f:
        magic, bsz, total, zero = struct.unpack('<4sIII', f.read(16))
        if magic != b'BDV2':
            return None, total
        cnt, rem = divmod(n - 16, 4 + SEC)
        if rem:
            return None, total
        idx = set()
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            idx.add(struct.unpack('<I', f.read(4))[0])
    return idx, total


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(
        REPO, 'third_party', 'orig', 'ps2', "Tom Clancy's Ghost Recon (USA).iso"))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)

    P('iso = %s' % a.iso)
    iso = T.Iso(a.iso)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    P('[menu] MENU.IMG LBA=%d ; 条目 %d 个 ; iso base = 0x%X' %
      (zx_lib.MENU_LBA, len(ent), zx_lib.MENU_LBA * SEC))
    P('% -4s %-24s %10s %10s %10s %12s %12s' %
      ('idx', 'name', 'off', 'stored', 'real', 'iso_off', 'iso_end'))
    for e in ent:
        P('%-4d %-24s 0x%08X %10d %10d %12d %12d' %
          (e['idx'], e['name'], e['off'], e['stored'], e['real'], e['iso_off'],
           e['iso_off'] + e['stored']))

    dumps = sorted(glob.glob(os.path.join(DUMPDIR, '*.dump')))
    idx_by = {}
    for d in dumps:
        i, _t = load_idx(d)
        if i is not None:
            idx_by[os.path.basename(d)] = i
    P('')
    P('可读 dump = %d 个' % len(idx_by))

    def cover(off0, size, label):
        l0 = off0 // SEC
        l1 = (off0 + size - 1) // SEC
        P('')
        P('── %s : iso 0x%X..0x%X (%d B) ; LBA %d..%d (%d 扇区)' %
          (label, off0, off0 + size, size, l0, l1, l1 - l0 + 1))
        for nm in sorted(idx_by):
            have = sum(1 for l in range(l0, l1 + 1) if l in idx_by[nm])
            if have:
                P('     %-52s %5d / %d (%.1f%%)' % (nm, have, l1 - l0 + 1,
                                                    100.0 * have / (l1 - l0 + 1)))
        union = set()
        for nm in idx_by:
            union |= idx_by[nm]
        have = sum(1 for l in range(l0, l1 + 1) if l in union)
        P('     [UNION] %d / %d (%.1f%%)' % (have, l1 - l0 + 1,
                                             100.0 * have / (l1 - l0 + 1)))

    for nm in ('FONT.RES', 'COMMON.PAK'):
        e = [x for x in ent if x['name'] == nm]
        if not e:
            P('!! 没有条目 %s' % nm)
            continue
        e = e[0]
        cover(e['iso_off'], e['stored'], nm)

    # COMMON.PAK 内部记录
    e_pak = [x for x in ent if x['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    P('')
    P('[pak] COMMON.PAK 记录 %d 条' % len(recs))
    P('% -24s %10s %10s %10s %10s %10s' % ('name', 'o0', 'o1', 'o2', 'stored', 'off'))
    for r in recs:
        P('%-24s %10d %10d %10d %10d %10d' % (r[0], r[1], r[2], r[3], r[5], r[6]))
    r = [x for x in recs if x[0] == 'new_font_revised']
    if r:
        r = r[0]
        cover(e_pak['iso_off'] + r[6], r[5], 'COMMON.PAK@new_font_revised (压缩态)')
    iso.close()
    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'fontloc.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
