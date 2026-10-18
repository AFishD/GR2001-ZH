# -*- coding: utf-8 -*-
r"""nh_stage12_ftrec.py — FONT.RES 解压后字表记录结构 EN vs ZH 对比 (只读)

口径来自 work/tools/zx_lib.ft_records:
  blob[24] = 面(face)记录数 ; 每面: u32 nameLen + name + 14 x u32 字段
  nrec = fld[4]*fld[5] ; 随后 nrec 条 10 字节记录 (b0,b1,u0,v0,u1,v1)
"""
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


def ft_records(blob, body_off=28):
    p = body_off
    n = struct.unpack_from('<I', blob, 24)[0]
    out = []
    for _ in range(n):
        if p + 4 > len(blob):
            out.append(('!!TRUNC', None, []))
            break
        l = struct.unpack_from('<I', blob, p)[0]
        p += 4
        nm = blob[p:p + l].decode('latin-1', 'replace')
        p += l
        if p + 56 > len(blob):
            out.append((nm, None, '!!TRUNC-FIELDS'))
            break
        fld = list(struct.unpack_from('<14I', blob, p))
        p += 56
        nrec = fld[4] * fld[5]
        rows = []
        for r in range(nrec):
            if p + 10 * r + 10 > len(blob):
                rows.append(('!!TRUNC-REC', r))
                break
            rows.append((p + 10 * r, struct.unpack_from('<BB4H', blob, p + 10 * r)))
        p += nrec * 10
        out.append((nm, fld, rows))
    return out, p, n


def load_fontres(iso, path):
    f = iso.files()[path]
    ents, _, _ = iso.img_entries(f['lba'], None)
    e = [x for x in ents if x['name'] == 'FONT.RES'][0]
    raw = iso.rd(f['lba'] * N.SEC + e['off'], e['stored'])
    L, S = struct.unpack_from('<II', raw, 0)
    dd, err, _ = tcslib.lzo1x_decompress(raw[8:8 + L], out_size=S)
    return e, raw, dd, L, S


def main():
    buf = io.StringIO()
    for path in ('/MENU.IMG;1', '/GR.IMG;1'):
        for tag in ('EN_ORIG', 'ZH113b_fix'):
            iso = N.Iso(N.ISO[tag])
            e, raw, dd, L, S = load_fontres(iso, path)
            iso.close()
            recs, used, nface = ft_records(dd)
            buf.write('=' * 96 + '\n%s %s FONT.RES: entry stored=%d real=%d ; '
                      '内部 comp=%d real=%d ; 解压得到 %d B\n'
                      % (tag, path, e['stored'], e['real'], L, S, len(dd)))
            buf.write('  blob[24] 面记录数 = %d ; 解析消耗 = %d / %d B ; 尾部剩余 = %d B\n'
                      % (nface, used, len(dd), len(dd) - used))
            tot = 0
            maxrecend = 0
            for (nm, fld, rows) in recs:
                if fld is None:
                    buf.write('  面 %r 字段截断\n' % nm)
                    continue
                nrec = fld[4] * fld[5] if isinstance(fld, list) else 0
                tot += len(rows) if isinstance(rows, list) else 0
                buf.write('  面 %-28r nameLen=%-3d fld=%s\n' % (nm, len(nm), fld))
                buf.write('       记录数 = fld[4]*fld[5] = %d*%d = %d ; 实得 %s\n'
                          % (fld[4], fld[5], nrec, len(rows) if isinstance(rows, list) else rows))
                # 统计 v 带 / u 带范围
                us, vs = [], []
                for it in (rows if isinstance(rows, list) else []):
                    if isinstance(it, tuple) and len(it) == 2 and isinstance(it[1], tuple):
                        b0, b1, u0, v0, u1, v1 = it[1]
                        us += [u0, u1]
                        vs += [v0, v1]
                if us:
                    buf.write('       u 范围 [%d,%d]  v 范围 [%d,%d]\n'
                              % (min(us), max(us), min(vs), max(vs)))
            buf.write('  合计记录 = %d\n' % tot)
            buf.write('  明文 md5 = %s\n' % __import__('hashlib').md5(dd).hexdigest())
    print(buf.getvalue())
    with open(os.path.join(N.EVID, 'stage12_ftrec.txt'), 'w', encoding='utf-8') as fh:
        fh.write(buf.getvalue())


if __name__ == '__main__':
    main()
