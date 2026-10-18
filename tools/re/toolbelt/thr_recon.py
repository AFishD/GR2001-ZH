# -*- coding: utf-8 -*-
r"""thr_recon.py -- round86 侦察: GR_ZH124 的 new_font_revised 记录 + 容器逐字节结构 (READ-ONLY)

用法: python tools/re/toolbelt/thr_recon.py <iso> [<iso> ...]
输出: 记录字段 / ISO 绝对偏移 / 容器 16 B 步进 hex / tcslib 段表 / 每段 48 B 头 hex
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'tools', 'text_csv')))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

SEC = 2048
MENU_LBA = tcslib.MENU_LBA


def hexdump(b, base=0, n=None, per=16):
    out = []
    n = len(b) if n is None else min(n, len(b))
    for o in range(0, n, per):
        chunk = b[o:o + per]
        out.append('  %08X  %s  |%s|' % (base + o,
                                         ' '.join('%02X' % c for c in chunk),
                                         ''.join(chr(c) if 32 <= c < 127 else '.' for c in chunk)))
    return out


def main(argv):
    for path in argv:
        print('=' * 100)
        print(path)
        iso = tcslib.Iso(path)
        print('  iso size %d B = %d 扇区' % (iso.size, iso.size // SEC))
        hdr = zx_lib.header(iso, MENU_LBA)
        ents = zx_lib.entries(iso, MENU_LBA)
        print('  IMG 声明 size=%d (0x%X) ; 条目 %d ; names %d..%d ; hash_off 0x%X'
              % (hdr['size'], hdr['size'], len(ents), hdr['names_start'], hdr['names_end'],
                 hdr['hash_off']))
        e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
        e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
        print('  COMMON.PAK #%d off=0x%X stored=%d real=%d iso_off=0x%X'
              % (e_pak['idx'], e_pak['off'], e_pak['stored'], e_pak['real'], e_pak['iso_off']))
        print('  FONT.RES   #%d off=0x%X stored=%d real=%d iso_off=0x%X'
              % (e_ft['idx'], e_ft['off'], e_ft['stored'], e_ft['real'], e_ft['iso_off']))
        last_end = max(e['off'] + e['stored'] for e in ents)
        print('  最后条目 end=%d ; IMG 尾料 %d B' % (last_end, hdr['size'] - last_end))

        pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
        print('  PAK %d B' % len(pak))
        recs = tcslib.parse_pak_records(pak)
        for r in recs:
            print('    rec %-20s psm=0x%02X %dx%d clut=%d px_size=0x%X px_off=0x%X end=0x%X'
                  % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[6] + r[5]))

        nm, psm, w, h, clut, px_size, px_off = recs[1]
        rec_off = px_off - 0x43C
        print('  ★ rec#1 @PAK+0x%X ; w@+0x%X h@+0x%X px_size@+0x%X'
              % (rec_off, rec_off + 0x1C, rec_off + 0x20, px_off - 4))
        print('  ★ ISO 绝对: rec=0x%X w=0x%X h=0x%X px_size=0x%X 容器=0x%X'
              % (e_pak['iso_off'] + rec_off, e_pak['iso_off'] + rec_off + 0x1C,
                 e_pak['iso_off'] + rec_off + 0x20, e_pak['iso_off'] + px_off - 4,
                 e_pak['iso_off'] + px_off))
        print('  记录头 0x18 B: %s' % pak[rec_off:rec_off + 0x18].hex(' '))
        print('  w=%d h=%d clut=%d px_size=0x%X(= %d)'
              % (w, h, clut, px_size, px_size))
        print('  理论裸像素 4bpp w*h/2 = %d = 0x%X ; px_size - 裸像素 = %d'
              % (w * h // 2, w * h // 2, px_size - w * h // 2))

        ct = bytes(pak[px_off:px_off + px_size])
        print('  容器 %d B (0x%X)' % (len(ct), len(ct)))
        print('  开头 256 B hexdump:')
        for line in hexdump(ct, 0, 256):
            print(line)
        segs = tcslib.atlas_container_segments(ct, w // 2)
        print('  tcslib 段表 (首行, 数据偏移, 字节数): %s' % (segs,))
        if segs:
            tot = sum(s[2] for s in segs)
            print('  段数 %d ; 段数据合计 %d B ; 段头合计 %d B ; 尾部 %d B'
                  % (len(segs), tot, len(segs) * 48,
                     len(ct) - tot - len(segs) * 48))
            for i, (row, doff, nb) in enumerate(segs):
                pre = ct[doff - 48:doff]
                print('    seg%d 首行=%-4d doff=0x%-7X nb=%-6d (%.4f 行) 头=%s'
                      % (i, row, doff, nb, nb / float(w // 2), pre.hex(' ')))
        print('  末尾 96 B hexdump:')
        for line in hexdump(ct, len(ct) - 96, 96):
            print(line)
        iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
