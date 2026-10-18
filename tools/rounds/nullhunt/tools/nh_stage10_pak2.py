# -*- coding: utf-8 -*-
r"""nh_stage10_pak2.py — COMMON.PAK 记录链 + FONT.RES 结构 校验 (只读)

- COMMON.PAK: 逐记录解析 (口径同 tools/re/toolbelt/root_atlas_layout.py),
  检查记录链是否在 stored(400,659) 内正常终止、尾部结构、px_size 不变式
- FONT.RES : LZO 子流解压, 检查 stored/real 与实际解压长度是否一致
"""
import io
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nh_lib as N   # noqa: E402


def pak_records(pak):
    """口径同 tools/re/toolbelt/root_atlas_layout.py: <u32 mode><u32 nl><name> + 模式体"""
    p, recs = 0, []
    while p + 8 <= len(pak):
        mode, nl = struct.unpack_from('<II', pak, p)
        if nl < 1 or nl > 64 or p + 8 + nl > len(pak):
            break
        nm = pak[p + 8:p + 8 + nl].split(b'\x00')[0].decode('latin-1', 'replace')
        r = p + 8 + nl
        if mode == 0:
            psm, w, h, clut_size = struct.unpack_from('<4I', pak, r)
            q = r + 16 + clut_size
            px_size, = struct.unpack_from('<I', pak, q)
            q += 4
            recs.append(dict(mode=mode, name=nm, off=p, psm=psm, w=w, h=h,
                             clut_size=clut_size, px_size=px_size, px_at=q,
                             end=q + px_size))
            p = q + px_size
        elif mode in (1, 2, 3):
            psm, w, h = struct.unpack_from('<3I', pak, r)
            q = r + 12
            clut_size = 0
            if psm in (0x13, 0x14):
                clut_size, = struct.unpack_from('<I', pak, q)
                q += 4 + clut_size
            px_size, = struct.unpack_from('<I', pak, q)
            q += 4
            recs.append(dict(mode=mode, name=nm, off=p, psm=psm, w=w, h=h,
                             clut_size=clut_size, px_size=px_size, px_at=q,
                             end=q + px_size))
            p = q + px_size
        else:
            break
    return recs


def main():
    buf = io.StringIO()
    for tag in ('EN_ORIG', 'ZH113b', 'ZH113b_fix'):
        iso = N.Iso(N.ISO[tag])
        f = iso.files()['/MENU.IMG;1']
        ents, hdr, names = iso.img_entries(f['lba'], None)
        base = f['lba'] * N.SEC
        for want in ('COMMON.PAK', 'FONT.RES'):
            e = [x for x in ents if x['name'] == want][0]
            pak = iso.rd(base + e['off'], e['stored'])
            buf.write('%-12s %-11s #%-4d off=%-10d stored=%-9d real=%-9d\n'
                      % (tag, want, e['idx'], e['off'], e['stored'], e['real']))
            if want == 'COMMON.PAK':
                recs = pak_records(pak)
                last = recs[-1]['end'] if recs else 0
                buf.write('    PAK=%d B, 记录数=%d, 最后记录 end=0x%X(%d), 尾料=%d B\n'
                          % (len(pak), len(recs), last, last, len(pak) - last))
                for r in recs:
                    buf.write('    rec @0x%-6X %-22s mode=%d psm=0x%-3X %4dx%-4d clut=%-6d '
                              'px_size=0x%-8X end=0x%X  px==w*h/2+16? %s  (w*h/2)%%2048=%d\n'
                              % (r['off'], r['name'], r['mode'], r['psm'], r['w'], r['h'],
                                 r['clut_size'], r['px_size'], r['end'],
                                 'YES' if r['px_size'] == r['w'] * r['h'] // 2 + 16 else 'NO',
                                 (r['w'] * r['h'] // 2) % 2048))
                z = len(pak) - len(pak.rstrip(b'\x00'))
                n63 = sum(1 for i in range(0, len(pak) - 4, 4)
                          if struct.unpack_from('<I', pak, i)[0] == 0x63)
                buf.write('    mo-wei-quan-ling = %d ; 4B-aligned 0x63 count = %d\n' % (z, n63))
                buf.write('    tail 16 B: %s\n' % pak[last:last + 16].hex(' '))
            else:
                subs = None
                try:
                    import tcslib
                    subs = tcslib.lzo_subs(pak)
                except Exception as ex:                      # noqa: BLE001
                    buf.write('    [lzo] fail: %s\n' % ex)
                if subs:
                    tot_c = sum(c for (_, c, _, _) in subs)
                    tot_r = sum(r for (_, _, r, _) in subs)
                    cover = subs[-1][3] + 8 + subs[-1][1]
                    buf.write('    LZO subs=%d : Sum(comp)=%d Sum(real)=%d ; cover %d / stored %d ; %s\n'
                              % (len(subs), tot_c, tot_r, cover, e['stored'],
                                 'COVERED' if cover == e['stored'] else 'NOT-EXACT'))
                    buf.write('    first sub real=%d ; entry real=%d ; %s\n'
                              % (subs[0][2], e['real'],
                                 'OK' if subs[0][2] == e['real'] else 'MISMATCH'))
                else:
                    buf.write('    LZO subs = 0\n')
                buf.write('    head 48 B: %s\n' % pak[:48].hex(' '))
        iso.close()
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage10_pak_fontres.txt'), 'w', encoding='utf-8') as fh:
        fh.write(buf.getvalue())


if __name__ == '__main__':
    main()
