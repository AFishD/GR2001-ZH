# -*- coding: utf-8 -*-
r"""lay_fontres.py —— 【GR_LAYOUT】只读解析盘上 FONT.RES：三面的 nrec / firstchar / 记录步长 / 矩形带。

用法: python lay_fontres.py <iso> [-o out.txt] [--atlas]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))

import zx_lib  # noqa: E402
import tcslib as T  # noqa: E402


def main():
    argv = sys.argv[:]
    outpath = None
    for opt in ('-o',):
        if opt in argv:
            i = argv.index(opt)
            outpath = argv[i + 1]
            del argv[i:i + 2]
    want_atlas = '--atlas' in argv
    if want_atlas:
        argv.remove('--atlas')
    out = open(outpath, 'w', encoding='utf-8', newline='\n') if outpath else sys.stdout
    if not outpath:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    iso_p = argv[1]
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    out.write('# ISO = %s\n' % os.path.abspath(iso_p))
    out.write('# MENU 条目:\n')
    for e in ent:
        out.write('   %-28s iso_off=0x%08X stored=%-8d real=%s\n'
                  % (e.get('name'), e['iso_off'], e['stored'], e.get('real')))
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    blob = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    out.write('\n# FONT.RES: 槽内 %d B → 展开 %d B\n' % (len(ft_slot), len(blob)))
    faces, end = zx_lib.ft_records(blob, 28)
    out.write('# 展开态尾部指针 = %d (blob=%d)\n' % (end, len(blob)))
    for (nm, fld, rows) in faces:
        out.write('\n## face %r\n' % nm)
        out.write('   fld[0..13] = %s\n' % ['0x%X' % x for x in fld])
        nrec = fld[4] * fld[5]
        out.write('   fld[4]*fld[5] = %d * %d = nrec = %d\n' % (fld[4], fld[5], nrec))
        out.write('   ★ base = fld[?] 候选: fld[8]=%d(0x%X) fld[9]=%d(0x%X) fld[10]=%d(0x%X) '
                  'fld[11]=%d(0x%X)\n' % (fld[8], fld[8], fld[9], fld[9], fld[10], fld[10],
                                          fld[11], fld[11]))
        # 记录统计
        ne = 0
        ext = [None, None, None, None]
        for (o, r) in rows:
            b0, b1, u0, v0, u1, v1 = r
            if u1 > u0 and v1 > v0:
                ne += 1
                for k, val in enumerate((u0, v0, u1, v1)):
                    ext[k] = val if ext[k] is None else (min(ext[k], val) if k < 2
                                                         else max(ext[k], val))
        out.write('   记录 %d 条；非空(矩形 u1>u0 且 v1>v0)= %d；矩形并集 = %s\n'
                  % (nrec, ne, ext))
        xs = sorted(set((r[2], r[3], r[4], r[5]) for (_o, r) in rows
                        if r[4] > r[2] and r[5] > r[3]))
        out.write('   不同矩形 = %d 个；前 6 个 = %s\n' % (len(xs), xs[:6]))
        if want_atlas:
            for (_o, r) in rows[:8]:
                out.write('     rec %s\n' % (r,))

    # ── 图集（COMMON.PAK）几何 ──
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    out.write('\n# COMMON.PAK 记录:\n')
    for r in recs:
        out.write('   %s\n' % (r,))
    iso.close()
    if outpath:
        out.close()
        print('[out] %s' % outpath)


if __name__ == '__main__':
    main()
