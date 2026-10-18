# -*- coding: utf-8 -*-
r"""cap_k2_records.py -- 只读: 全量 FT 记录清单 + 采样窗语义实测 + 新布局冲突面

用法: python tools/re/toolbelt/cap_k2_records.py [--art 41,25,0x96]
"""
import argparse
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

W = 1024
DU, DV = T.GLYPH_DU, T.GLYPH_DV
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip):
    return 2 + 16 * (row + (skip if row >= 12 else 0))


def cell(slot, ncol, skip):
    return 16 * (slot % ncol), yrow(slot // ncol, skip)


def plane_of(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, _cov = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    ft = b''.join(s[0] for s in T.lzo_subs(bytes(iso.read(e_ft['iso_off'], e_ft['stored']))))
    faces, endp = zx_lib.ft_records(ft, 28)
    iso.close()
    return img, faces, endp, rec


def art(img, u0, v0, u1, v1, tag=''):
    P('    ┌─ %s rect=(%d,%d,%d,%d) %dx%d' % (tag, u0, v0, u1, v1, u1 - u0, v1 - v0))
    for y in range(max(0, v0), min(img.shape[0], v1)):
        P('    │' + ''.join('#' if img[y, x] else '.' for x in range(u0, u1)))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH124',
                                                 'GR_ZH124.iso'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    img, faces, endp, rec = plane_of(a.iso)
    P('=' * 96)
    P('cap_k2_records.py  iso=%s  (%dx%d)' % (a.iso, rec[2], rec[3]))
    # ── 全量非空记录, 按 (v0,v1) 分组 ──
    byband = {}
    allrec = []
    for fi, (nm, fld, rows) in enumerate(faces):
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3]:
                allrec.append((fi, nm, k, o, r))
                byband.setdefault((r[3], r[5]), []).append((fi, nm, k, o, r))
    P('[rec] 非空记录 **%d** 条 (共 %d 条)' % (len(allrec), sum(len(f[2]) for f in faces)))
    P('[rec] v 带分组 (v0,v1) → 条数 / u0 集合 / x>=992 条数:')
    for (b, lst) in sorted(byband.items()):
        u0s = sorted({r[2] for (_f, _n, _k, _o, r) in lst})
        nstrip = sum(1 for (_f, _n, _k, _o, r) in lst if r[2] >= 992)
        P('    v %4d..%-4d (%2d 条) u0 ∈ %s%s'
          % (b[0], b[1], len(lst),
             ('%d..%d (%d 个)' % (u0s[0], u0s[-1], len(u0s))) if len(u0s) > 6 else u0s,
             '  ★ x>=992: %d' % nstrip if nstrip else ''))
    # ── 墨量检查: 每条记录的墨 ──
    P('')
    P('[ink] 逐记录墨量 (rect 内 / rect+%d,%d 内): 只列 0 墨或异常' % (DU, DV))
    zero = []
    for (fi, nm, k, o, r) in allrec:
        b0, b1, u0, v0, u1, v1 = r
        n1 = int(img[v0:v1, u0:u1].sum())
        n2 = int(img[v0 + DV:v1 + DV, u0 + DU:u1 + DU].sum())
        if n1 == 0:
            zero.append((nm, k, r))
    P('[ink] rect 内 **0 墨** 的记录 **%d** 条 (这些是"宽空格"类):' % len(zero))
    seen = {}
    for (nm, k, r) in zero:
        seen.setdefault(r, []).append((nm, k))
    for r, v in sorted(seen.items()):
        P('      rect=(%d,%d,%d,%d) ← %s' % (r[2], r[3], r[4], r[5],
                                              ['%s#%d(0x%02X)' % (n, k, k + 0x20) for (n, k) in v]))
    # ── 采样窗语义实测: 对 u0<992 且 rect 内有墨的 8x16 记录, 画 ASCII art ──
    P('')
    P('[win] ★ 采样窗语义: 若"记录矩形"就是采样窗, 则 rect 内的墨应当构成**完整可读**的字形')
    art_keys = [33, 65, 87, 1, 15, 56, 118, 124, 96, 207, 96 + 0]
    shown = set()
    for (fi, nm, k, o, r) in allrec:
        if nm != 'large' or k not in art_keys or k in shown:
            continue
        shown.add(k)
        art(img, r[2], r[3], r[4], r[5], '%s#%d code=0x%02X' % (nm, k, k + 0x20))
    # ── 新布局冲突: 记录窗 ∩ 新网格格 ──
    P('')
    P('[new] 新布局 (h=644/64 列/SKIP=2) 下: 记录窗 ∩ 网格格 的**逐条**统计')
    ncol, skip, h = 64, 2, 644
    cells = {}
    for s in range(0, 2350):
        cells[cell(s, ncol, skip)] = s
    def hits(r, du, dv):
        u0, v0, u1, v1 = r[2] + du, r[3] + dv, r[4] + du, r[5] + dv
        out = []
        for (x, y), s in cells.items():
            if u0 < x + 16 and x < u1 and v0 < y + 16 and y < v1:
                out.append(s)
        return out
    for tagw, du, dv in (('rect 原值', 0, 0), ('rect+%d,%d' % (DU, DV), DU, DV)):
        P('  ── 口径: %s' % tagw)
        cnt = {}
        for (fi, nm, k, o, r) in allrec:
            hs = hits(r, du, dv)
            if hs:
                cnt.setdefault(nm, []).append((k, r, hs))
        for nm in sorted(cnt):
            lst = cnt[nm]
            P('     %-8s 相交记录 **%d** 条' % (nm, len(lst)))
            for (k, r, hs) in lst:
                P('        #%-4d code=0x%02X rect=(%4d,%3d,%4d,%3d) → 槽 %d..%d (%d 个)'
                  % (k, k + 0x20, r[2], r[3], r[4], r[5], min(hs), max(hs), len(hs)))
    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'temp',
                                'k2_records.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
