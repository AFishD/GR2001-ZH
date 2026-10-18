# -*- coding: utf-8 -*-
r"""nh_stage11_fontres.py — FONT.RES 内部 LZO 子流结构逐盘核对 (只读)"""
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import nh_lib as N   # noqa: E402
import tcslib        # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def walk(raw, label, buf):
    p = 0
    k = 0
    while p + 8 <= len(raw):
        L, S = struct.unpack_from('<II', raw, p)
        ok = False
        try:
            dd, err, _ = tcslib.lzo1x_decompress(raw[p + 8:p + 8 + L], out_size=S)
            ok = (err is None and len(dd) == S)
        except Exception as ex:                                  # noqa: BLE001
            dd, err = b'', repr(ex)
        buf.write('    sub#%d @0x%-6X L=%-8d S=%-8d end=%-8d  解压 %s%s\n'
                  % (k, p, L, S, p + 8 + L, 'OK' if ok else 'FAIL(%s)' % err,
                     '' if ok else ''))
        if not ok:
            break
        p += 8 + L
        k += 1
    buf.write('    -> 子流 %d 个, 解析覆盖 %d / %d B, 残余 %d B\n'
              % (k, p, len(raw), len(raw) - p))
    if p < len(raw):
        buf.write('    -> 残余头 32 B: %s\n' % raw[p:p + 32].hex(' '))


def main():
    buf = io.StringIO()
    for tag in ('EN_ORIG', 'ZH113b', 'ZH113b_fix'):
        iso = N.Iso(N.ISO[tag])
        for path, lba in (('/MENU.IMG;1', None), ('/GR.IMG;1', None)):
            f = iso.files()[path]
            ents, hdr, names = iso.img_entries(f['lba'], None)
            base = f['lba'] * N.SEC
            for e in ents:
                if e['name'] != 'FONT.RES':
                    continue
                raw = iso.rd(base + e['off'], e['stored'])
                buf.write('%-12s %-13s FONT.RES #%-4d off=%-10d stored=%-8d real=%-8d\n'
                          % (tag, path, e['idx'], e['off'], e['stored'], e['real']))
                buf.write('    头 16 B: %s\n' % raw[:16].hex(' '))
                u = struct.unpack_from('<4I', raw, 0)
                buf.write('    头 u32[0..3] = %s  (u32[0]+8=%d %s stored; u32[1]=%d %s real)\n'
                          % (u, u[0] + 8, '==' if u[0] + 8 == e['stored'] else '!=',
                             u[1], '==' if u[1] == e['real'] else '!='))
                walk(raw, tag, buf)
        iso.close()
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage11_fontres_streams.txt'), 'w', encoding='utf-8') as fh:
        fh.write(buf.getvalue())


if __name__ == '__main__':
    main()
