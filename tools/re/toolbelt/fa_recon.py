# -*- coding: utf-8 -*-
r"""fa_recon.py — GR_FA2400 前置侦察（只读）: 采样窗口径标定 + 5 个借槽的源窗取证

回答的问题:
  ① 基底盘 (GR_ZH113b / GR_ZH124 / GR_MERGE2400) 的图集几何 (w,h,ncol) 与 FT 记录
  ② ★ 采样窗口径: 用 r84 已证的「基底裸 0xB4 的采样窗 == 「用」对偶格」**反解偏移 (du,dv)**
     —— 再把这个偏移套到 idx 150..153 (击/小/时/按) 与 idx 145/149 (0xB1/0xB5 图标占位)
  ③ 0xB1(△)/0xB5(✕) 的图标来源: FT 记录是否为空窗口 (空 ⇒ 必须停手回报)
  ④ 把候选窗口/格位渲染成 PNG 供人眼确认

    python tools/re/toolbelt/fa_recon.py --iso work/builds/GR_ZH113b/GR_ZH113b.iso --tag base113b
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                     # noqa: E402
import tcslib as T                                                     # noqa: E402
import zx_lib                                                          # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def container_to_plane(cont, w, h):
    """与 cap_build.py 同一实现 (引擎口径像素面)。"""
    stride = w // 2
    segs = [s for s in T.atlas_container_segments(bytes(cont), stride) if s[2] > 0]
    plane = bytearray(b'\x11' * (stride * h))
    for (row0, doff, nb) in segs:
        nfull, rest = nb // stride, nb % stride
        for i in range(nfull):
            if row0 + i < h:
                plane[(row0 + i) * stride:(row0 + i + 1) * stride] = \
                    cont[doff + i * stride:doff + (i + 1) * stride]
        if rest and row0 + nfull < h:
            d = (row0 + nfull) * stride
            plane[d:d + rest] = cont[doff + nfull * stride:doff + nfull * stride + rest]
    return bytes(plane), segs


def window(plane, w, x0, y0, ww, hh):
    """引擎口径窗口取墨 (nibble==0 为墨)。x0/y0 为左上角。"""
    stride = w // 2
    g = np.zeros((hh, ww), dtype=bool)
    for i in range(hh):
        y = y0 + i
        for j in range(ww):
            x = x0 + j
            b = plane[y * stride + x // 2]
            v = (b >> 4) if (x & 1) else (b & 0x0F)
            g[i, j] = (v == 0)
    return g


def cell(slot, ncol):
    row, col = slot // ncol, slot % ncol
    return 16 * col, 2 + 16 * (row + (3 if row >= 12 else 0))


def read_font(iso_path):
    iso = T.Iso(iso_path)
    ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    nm, psm, w, h, clut, px_size, PX = recs[1]
    ct = pak[PX:PX + px_size]
    plane, segs = container_to_plane(ct, w, h)
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    ft_blob = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, ft_end = zx_lib.ft_records(ft_blob, 28)
    iso.close()
    return dict(path=iso_path, w=w, h=h, psm=psm, px_size=px_size, name=nm,
                plane=plane, segs=segs, faces=faces, ft_slot=len(ft_slot),
                ft_blob=ft_blob, ft_end=ft_end, ct=ct, PX=PX, pak_len=len(pak),
                e_pak=e_pak)


def png(g, path, scale=8):
    from PIL import Image
    a = np.where(g, 0, 255).astype(np.uint8)
    im = Image.fromarray(a, 'L').resize((g.shape[1] * scale, g.shape[0] * scale), Image.NEAREST)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--ncol', type=int, default=None)
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    P('=' * 92)
    P('fa_recon.py  iso=%s' % a.iso)
    P('=' * 92)
    F = read_font(a.iso)
    P('[font] %s psm=0x%X %dx%d px_size=0x%X ; PAK %d B ; 容器段 %d'
      % (F['name'], F['psm'], F['w'], F['h'], F['px_size'], F['pak_len'], len(F['segs'])))
    P('[ft  ] FONT.RES 槽 %d B / 展开 %d B ; body_end=%d' % (F['ft_slot'], len(F['ft_blob']), F['ft_end']))
    for (nm, fld, rows) in F['faces']:
        ne = sum(1 for (_o, r) in rows if r[4] > r[2] and r[5] > r[3])
        P('[ft  ] face %-8s nrec=%d (fld[4]*fld[5]=%d) 非空 %d ; fld=%s'
          % (nm, len(rows), fld[4] * fld[5], ne, fld))

    rep = dict(iso=a.iso, w=F['w'], h=F['h'], px_size=F['px_size'],
               faces=[dict(name=nm, fld=fld, nrec=len(rows)) for (nm, fld, rows) in F['faces']])

    # ── ① 采样窗偏移标定: 用 r84 的「用」口径反解 ──
    #    码 c 的对偶 pair = (0xB1, c - 0xB1 + 0xA1) ⇒ slot = (0xB1-0xA1)*94 + (trail-0xA1)
    P('')
    P('① 采样窗偏移标定 (r84「用」口径): 找 (du,dv) 使 FT[idx=code-0x20] 的 (u0+du,v0+dv) 16x16')
    P('   == 该码对偶 pair 的引擎格 (slot=(0xB1-0xA1)*94+(trail-0xA1))')
    calib = {}
    for code in (0xB2, 0xB3, 0xB4):
        idx = code - 0x20
        trail = code - 0xB1 + 0xA1
        slot = (0xB1 - 0xA1) * 94 + (trail - 0xA1)
        for (nm, fld, rows) in F['faces']:
            if idx >= len(rows):
                continue
            _o, r = rows[idx]
            u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
            found = []
            for du in range(-8, 9):
                for dv in range(-8, 9):
                    if u0 + du < 0 or v0 + dv < 0:
                        continue
                    got = None
                    for ncol in ([a.ncol] if a.ncol else [62, 64]):
                        cx, cy = cell(slot, ncol)
                        if u1 - u0 == 16 and v1 - v0 == 16:
                            got = (ncol, cx, cy)
                            win = window(F['plane'], F['w'], u0 + du, v0 + dv, 16, 16)
                            cw = window(F['plane'], F['w'], cx, cy, 16, 16)
                            if (win == cw).all():
                                found.append((ncol, du, dv, int(cw.sum())))
                    del got
            calib.setdefault(code, []).append((nm, (u0, v0, u1, v1), found))
            P('   code 0x%02X idx=%3d slot=%4d face %-8s rec=(%d,%d)-(%d,%d) %dx%d  匹配(du,dv,ncol,墨): %s'
              % (code, idx, slot, nm, u0, v0, u1, v1, u1 - u0, v1 - v0, found))
    rep['calib'] = {('0x%02X' % c): [(nm, list(r), [list(x) for x in f]) for (nm, r, f) in v]
                    for c, v in calib.items()}

    # ── ② 5 个借槽 + 0xB1/0xB5 的源窗取证 ──
    P('')
    P('② 候选码的 FT 记录三维对照 (idx = code - 0x20) + 采样窗墨量')
    cand = {0xB1: '△(图标占位)', 0xB5: '✕(图标占位)', 0xB6: '击', 0xB7: '小', 0xB8: '时',
            0xB9: '按', 0xBA: '战', 0xB2: '键', 0xB3: '练', 0xB4: '用'}
    det = {}
    for code in sorted(cand):
        idx = code - 0x20
        entry = dict(code='0x%02X' % code, char=cand[code], idx=idx, faces={})
        P('   ── 0x%02X %s  idx=%d' % (code, cand[code], idx))
        for (nm, fld, rows) in F['faces']:
            if idx >= len(rows):
                P('      %-8s (nrec=%d 越界)' % (nm, len(rows)))
                continue
            _o, r = rows[idx]
            u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
            ink = None
            if u1 > u0 and v1 > v0 and v1 + 4 <= F['h'] and u1 + 8 <= F['w']:
                win = window(F['plane'], F['w'], u0, v0, min(u1 - u0, 24), min(v1 - v0, 24))
                ink = int(win.sum())
            b0, b1 = r[0], r[1]
            P('      %-8s rec=(%d,%d)-(%d,%d) %dx%d  b0=0x%02X b1=0x%02X 窗内墨=%s'
              % (nm, u0, v0, u1, v1, u1 - u0, v1 - v0, b0, b1, ink))
            entry['faces'][nm] = dict(u0=u0, v0=v0, u1=u1, v1=v1, ink=ink)
        det['0x%02X' % code] = entry
    rep['records'] = det

    # ── ③ 图集里的图标嫌疑格 + 三个 face 的采样窗 PNG ──
    P('')
    P('③ 图集格位抽查 (△ 已在 slot 1504; 图标路径 slot = (lead-0xA1)*94+0xE0 ⇒ 0xB1→1728, 0xB5→2104)')
    ncols = [a.ncol] if a.ncol else [62, 64]
    for ncol in ncols:
        for slot in (1504, 1505, 1506, 1507, 1728, 2104):
            cx, cy = cell(slot, ncol)
            if cy + 16 > F['h'] or cx + 16 > F['w']:
                P('   ncol=%d slot=%4d -> (%4d,%3d) 越界 (h=%d)' % (ncol, slot, cx, cy, F['h']))
                continue
            g = window(F['plane'], F['w'], cx, cy, 16, 16)
            P('   ncol=%d slot=%4d -> (%4d,%3d) 墨=%3d' % (ncol, slot, cx, cy, int(g.sum())))
            if ncol == ncols[-1]:
                png(g, os.path.join(OUT, 'cells_%s' % a.tag, 'slot%04d.png' % slot))
    # 三个 face 的 idx 145..153 采样窗 (按记录原样, 不偏移)
    for (nm, fld, rows) in F['faces']:
        for idx in range(145, 154):
            if idx >= len(rows):
                continue
            _o, r = rows[idx]
            u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
            if u1 - u0 != 16 or v1 - v0 != 16 or u0 < 0 or v0 < 0 or u1 > F['w'] or v1 > F['h']:
                continue
            g = window(F['plane'], F['w'], u0, v0, 16, 16)
            png(g, os.path.join(OUT, 'rec_%s' % a.tag, '%s_idx%03d_code%02X_ink%d.png'
                                % (nm, idx, idx + 0x20, int(g.sum()))))

    with io.open(os.path.join(OUT, 'recon_%s.json' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(extra=rep, log=LOG), f, ensure_ascii=False, indent=1)
    P('')
    P('[out] %s' % os.path.join(OUT, 'recon_%s.json' % a.tag))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
