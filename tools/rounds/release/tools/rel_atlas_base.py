# -*- coding: utf-8 -*-
r"""rel_atlas_base.py -- 交付候选的**图集/字形/ASCII 表**独立核对 (不依赖已丢失的 GR_ZH124 / GR_F364)

    python work\builds\GR_RELEASE\tools\rel_atlas_base.py ^
        --iso  work\builds\GR_RELEASE\GR_ZH2400_FINAL.iso ^
        --base work\builds\GR_REBUILD\GR_REBUILD2400.iso ^
        --allpat work\builds\GR_REBUILD\GR_REBUILD2400_allpat.iso ^
        --out  work\builds\GR_RELEASE\temp

复用工程既有解析库 (tcslib / zx_lib / cap_build) 而**自己写判据**, 因为:
  * 原判据 (GR_FA2400_K2 §14/§16.4) 的参照盘 `GR_ZH124.iso` / `GR_F364.iso` 已不在磁盘上;
  * 本轮的直接基底 `GR_REBUILD2400.iso` 存在且**几何相同** (1024x644 / 64 列 / SKIP=2 / Y0=3)
    ⇒ 可以做"逐 texel == 基底"的**同几何**版本, 这是比旧版更强的对照 (不需重映射)。

判据:
  [A] 三闸门 (从盘上读)
  [B] 槽 0..2349 几何: 越界 0 / 格位重复 0 / V1_max <= h
  [C] 图集平面 final vs base 逐字节 (整面 + 逐槽 2350 个)
  [D] 保留槽 1872..2344 全空 (473) ; 有字形槽 0..1871 + 2345..2349 有墨
  [E] 借槽 2345..2349 逐 texel == 模板 (handoff JSON + 自制 ✕)
  [F] ASCII 表 182 条 (码位 0x21..0x9C): 记录 → 矩形 与 base 相同 且 逐 texel 相同
  [G] allpat 盘 2350 槽图案全解码
"""
import argparse
import collections
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import cap_build as CB                                                # noqa: E402

W, H = 1024, 644
NCOL, SKIP, Y0 = 64, 2, 3
NSLOTS, LIVE_HI, RES_LO, RES_HI, R84_LO, R84_HI = 2350, 1735, 1872, 2344, 1736, 1871
LEAD_HI = 0xBA
HANDOFF = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'temp', 'handoff',
                       'glyph_handoff.json')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip, y0):
    return y0 + 16 * (row + (skip if row >= 12 else 0))


def cell(slot, ncol=NCOL, skip=SKIP, y0=Y0):
    return 16 * (slot % ncol), yrow(slot // ncol, skip, y0)


def raw_to_ink(raw, h, w=W):
    stride = w // 2
    a = np.frombuffer(bytes(raw[:stride * h]), dtype=np.uint8).reshape(h, stride)
    out = np.zeros((h, w), dtype=bool)
    out[:, 0::2] = (a & 0x0F) == 0
    out[:, 1::2] = (a >> 4) == 0
    return out


def open_font(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    raw, segs = CB.container_to_plane(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    faces, _end = zx_lib.ft_records(b''.join(s[0] for s in T.lzo_subs(ft_slot)), 28)
    iso.close()
    return dict(rec=rec, raw=raw, segs=segs, ft_slot=ft_slot, faces=faces, pak=pak,
                e_pak=e_pak, e_ft=e_ft, ink=raw_to_ink(raw, rec[3]))


def xmark():
    g = np.zeros((16, 16), dtype=bool)
    for k in range(13):
        g[1 + k, 1 + k] = True
        g[1 + k, 13 - k] = True
    return g


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--base', required=True)
    ap.add_argument('--allpat', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--charset', default=None)
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    res = {}
    P('=' * 100)
    P('rel_atlas_base.py -- 图集/字形/ASCII 独立核对')
    P('  iso  = %s' % os.path.abspath(a.iso))
    P('  base = %s   ★ 参照 = 本产品线的直接基底 (同几何)' % os.path.abspath(a.base))
    P('=' * 100)

    f = open_font(a.iso)
    b = open_font(a.base)
    w, h, px = f['rec'][2], f['rec'][3], f['rec'][5]
    # ── [A] ──
    g1 = w < 1025
    g2 = (px == w * h // 2 + 16)
    g3 = ((w * h // 2) % 2048 == 0)
    g4 = px <= 329744
    P('[A] 三闸门 (从盘上读):')
    P('    w = %d (w<1025) %s' % (w, '✓' if g1 else '✗'))
    P('    px_size = %d == w*h/2+16 = %d %s' % (px, w * h // 2 + 16, '✓' if g2 else '✗'))
    P('    (w*h/2)%%2048 = %d %s' % ((w * h // 2) % 2048, '✓' if g3 else '✗'))
    P('    px_size <= 329,744 %s' % ('✓' if g4 else '✗'))
    P('    容器 %d B / %d 段 ; payload %d == w*h/2 - %d*48 %s'
      % (len(f['raw']), len(f['segs']), sum(s[2] for s in f['segs']), len(f['segs']),
         '✓' if sum(s[2] for s in f['segs']) == w * h // 2 - len(f['segs']) * 48 else '✗'))
    P('    base 同口径: w=%d h=%d px_size=%d (几何与产物盘相同: %s)'
      % (b['rec'][2], b['rec'][3], b['rec'][5],
         '✓' if (b['rec'][2], b['rec'][3], b['rec'][5]) == (w, h, px) else '✗'))
    res['A_gates'] = dict(w=w, h=h, px_size=px, gate1=bool(g1), gate2=bool(g2),
                          gate3=bool(g3), gate4=bool(g4),
                          container_bytes=len(f['raw']), segs=len(f['segs']))

    # ── [B] ──
    oob, dup, cells = [], [], {}
    for s in range(NSLOTS):
        x, y = cell(s)
        if not (0 <= x and x + 16 <= w and 0 <= y and y + 16 <= h):
            oob.append((s, x, y))
        if (x, y) in cells:
            dup.append((s, cells[(x, y)]))
        cells[(x, y)] = s
    nrow = max(s // NCOL for s in range(NSLOTS)) + 1
    v1max = yrow(nrow - 1, SKIP, Y0) + 16
    P('[B] 槽 0..%d 几何: 越界 %d / 格位重复 %d / 不同格位 %d ; 用到行 0..%d ; '
      'V1_max = %d <= h %d %s'
      % (NSLOTS - 1, len(oob), len(dup), len(cells), nrow - 1, v1max, h,
         '✓' if (not oob and not dup and v1max <= h) else '✗'))
    res['B_slots'] = dict(oob=oob, dup=dup, distinct=len(cells), rows=nrow,
                          v1_max=v1max, ok=bool(not oob and not dup and v1max <= h))

    # ── [C] 图集平面 ──
    ra, rb = np.frombuffer(bytes(f['raw']), dtype=np.uint8), np.frombuffer(bytes(b['raw']),
                                                                           dtype=np.uint8)
    same_plane = (ra.shape == rb.shape) and bool((ra == rb).all())
    nd = int((ra != rb).sum()) if ra.shape == rb.shape else -1
    bad_cells = []
    for s in range(NSLOTS):
        ga = CB.cell_read(f['raw'], *cell(s))
        gb = CB.cell_read(b['raw'], *cell(s))
        if not (ga == gb).all():
            bad_cells.append(s)
    P('[C] 图集平面 final vs base: 面偏移字节 %d ; 逐槽 0..%d 逐 texel 相同 **%d/%d** %s'
      % (nd, NSLOTS - 1, NSLOTS - len(bad_cells), NSLOTS, '✓' if not bad_cells else '✗'))
    P('    整面逐字节相同: %s (ink final %d / base %d)'
      % ('✓' if same_plane else '✗', int(f['ink'].sum()), int(b['ink'].sum())))
    res['C_plane'] = dict(diff_bytes=nd, cells_equal=NSLOTS - len(bad_cells),
                          cells_total=NSLOTS, bad=bad_cells[:20],
                          plane_identical=bool(same_plane),
                          ink_final=int(f['ink'].sum()), ink_base=int(b['ink'].sum()))

    # ── [D] 保留槽 / 有字形槽 ──
    n_res_ink = [s for s in range(RES_LO, RES_HI + 1) if CB.cell_read(f['raw'], *cell(s)).any()]
    live_empty = [s for s in range(0, LIVE_HI + 1)
                  if not CB.cell_read(f['raw'], *cell(s)).any()]
    r84_empty = [s for s in range(R84_LO, R84_HI + 1)
                 if not CB.cell_read(f['raw'], *cell(s)).any()]
    P('[D] 保留槽 %d..%d 全空: **%d/%d** %s (有墨 %s)'
      % (RES_LO, RES_HI, (RES_HI - RES_LO + 1) - len(n_res_ink), RES_HI - RES_LO + 1,
         '✓' if not n_res_ink else '✗', n_res_ink[:8]))
    P('    有字形槽: 现役 0..%d 空白 %d 个 %s ; r83/r84 %d..%d 空白 %d 个 %s'
      % (LIVE_HI, len(live_empty), '✓' if not live_empty else '✗',
         R84_LO, R84_HI, len(r84_empty), '✓' if not r84_empty else '✗'))
    n_glyph = (LIVE_HI + 1 - len(live_empty)) + (R84_HI - R84_LO + 1 - len(r84_empty)) + 5
    P('    ⇒ 有字形槽合计 = %d (现役 %d + r84 %d + 借槽 5) ; 保留空槽 %d'
      % (n_glyph, LIVE_HI + 1 - len(live_empty), R84_HI - R84_LO + 1 - len(r84_empty),
         RES_HI - RES_LO + 1))
    res['D_slots'] = dict(reserved_ink=n_res_ink, live_empty=live_empty,
                          r84_empty=r84_empty, glyph_slots=n_glyph,
                          reserved_slots=RES_HI - RES_LO + 1)

    # ── [E] 借槽 ──
    hd = json.load(io.open(HANDOFF, encoding='utf-8'))
    tmpl = {}
    for it in hd['items']:
        tmpl[it['slot']] = (np.array(it['bitmap'], dtype=int) == 0)
    tmpl[2349] = xmark()
    bad_bor = []
    for s, ink in sorted(tmpl.items()):
        got = CB.cell_read(f['raw'], *cell(s))
        if not (got == ink).all():
            bad_bor.append((s, int((got != ink).sum())))
    P('[E] 借槽 2345..2349 逐 texel == 模板: %s (不符 %s) ; 各槽墨量 %s'
      % ('✓' if not bad_bor else '✗', bad_bor,
         {s: int(CB.cell_read(f['raw'], *cell(s)).sum()) for s in sorted(tmpl)}))
    res['E_borrow'] = dict(bad=bad_bor, ok=bool(not bad_bor),
                           ink={str(s): int(CB.cell_read(f['raw'], *cell(s)).sum())
                                for s in sorted(tmpl)})

    # ── [F] ASCII 182 条 ──
    # 口径沿用原判据 (§16.4/§12.2(d)): 取**基底盘**里落在 ASCII 条带 (x>=992) 的记录,
    # 逐条比对"产物盘同 face/同 idx 的记录 → 矩形 与 逐 texel"。空记录 (ink 0) 只要求
    # 与基底**相同** (它们本来就是占位/空字形, 不能要求有墨)。
    def strip_of(fo):
        ft = b''.join(s[0] for s in T.lzo_subs(fo['ft_slot']))
        faces, _ = zx_lib.ft_records(ft, 28)
        offn = {fn: rows[0][0] for (fn, fld, rows) in faces}
        st = {}
        for (fn, fld, rows) in faces:
            for k, (o, r) in enumerate(rows):
                if r[4] > r[2] and r[5] > r[3] and r[2] >= 992:
                    st.setdefault((fn, k, k + 0x20), (o, tuple(r)))
        return ft, offn, st
    ftf, off_f, stf = strip_of(f)
    ftb, off_b, stb = strip_of(b)
    rects_b = {(fn, k): r for ((fn, k, _c), (_o, r)) in stb.items()}
    P('[F] ASCII 条带 (基底 x>=992): 基底 **%d** 个不同矩形 / **%d** 条记录 ; '
      '产物盘同口径 %d 条'
      % (len(set(rects_b.values())), len(stb), len(stf)))
    n_eq, bad, moved, n_ink = 0, [], 0, 0
    for key in sorted(stb):
        of, rf = stf.get(key, (None, None))
        ob, rb_ = stb[key]
        if rf is None:
            bad.append((key, '产物盘缺此记录'))
            continue
        inkf = f['ink'][rf[1]:rf[3], rf[0]:rf[2]]
        inkb = b['ink'][rb_[1]:rb_[3], rb_[0]:rb_[2]]
        ok = inkf.shape == inkb.shape and (inkf == inkb).all()
        n_eq += 1 if ok else 0
        n_ink += 1 if inkb.any() else 0
        moved += 1 if tuple(rf) != tuple(rb_) else 0
        if not ok:
            bad.append((key, 'ink 不同', dict(base=list(rb_), new=list(rf)),
                        int(inkb.sum()), int(inkf.sum())))
    P('    逐 texel == 基底 **%d/%d** %s ; 其中相对基底被搬 %d 条 ; 有墨记录 %d 条'
      % (n_eq, len(stb), '✓' if not bad else '✗ %s' % bad[:5], moved, n_ink))
    n_faces = len(f['faces'])
    n_rec = sum(len(rows) for (_fn, _fld, rows) in f['faces'])
    P('    FONT.RES faces %d / 记录 %d (base %d / %d)'
      % (n_faces, n_rec, len(b['faces']), sum(len(rows) for (_f, _l, rows) in b['faces'])))
    res['F_ascii'] = dict(rects_base=len(set(rects_b.values())), records_base=len(stb),
                          records_final=len(stf), equal=n_eq, bad=bad[:20], moved=moved,
                          inked=n_ink, ok=bool(not bad),
                          faces=n_faces, ft_records=n_rec)

    # ── [F2] K2 轮记录的 182 条 ASCII 证明, 在**成品盘**上逐条复核 ──
    # 参照盘 GR_ZH124 已不存在 ⇒ 用 K2 轮落盘的逐条证明 (base/new 矩形 + 墨量 + equal)
    # 作为"基底侧真值", 在成品盘上重算 FT 矩形与墨量, 必须逐条相符。
    K2PROOF = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'temp', 'dump_k2_final',
                           'ascii_182_records.json')
    if os.path.isfile(K2PROOF):
        pr = json.load(io.open(K2PROOF, encoding='utf-8'))
        faces_by = {}
        ftf2 = b''.join(s[0] for s in T.lzo_subs(f['ft_slot']))
        for (fn, _fld, rows) in zx_lib.ft_records(ftf2, 28)[0]:
            faces_by[fn] = rows[0][0]
        n_ok, n_bad = 0, []
        for it in pr:
            o2 = faces_by[it['face']] + it['idx'] * 10
            _b0, _b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', ftf2, o2)
            got = [u0, v0, u1, v1]
            ink = int(f['ink'][v0:v1, u0:u1].sum())
            ok = (got == list(it['new']) and ink == it['ink'] and it.get('equal'))
            n_ok += 1 if ok else 0
            if not ok:
                n_bad.append((it['face'], it['idx'], it['code'], it['new'], got,
                              it['ink'], ink))
        P('[F2] K2 轮记录的 **182** 条 ASCII 证明在成品盘上复核: **%d/182** %s (不符 %s)'
          % (n_ok, '✓' if not n_bad else '✗', n_bad[:5]))
        res['F2_ascii182'] = dict(proof=K2PROOF, ok=n_ok, total=len(pr), bad=n_bad[:10],
                                  pass_=bool(not n_bad and n_ok == 182))
    else:
        P('[F2] 未达成: K2 轮的 ascii_182_records.json 不在盘上 (%s)' % K2PROOF)
        res['F2_ascii182'] = dict(proof=None, pass_=None)

    # ── [G] allpat ──
    ap_ok = None
    if a.allpat and os.path.isfile(a.allpat):
        g = open_font(a.allpat)
        good, badp = 0, []
        for s in range(NSLOTS):
            ok, got, why = CB.pattern_decode(CB.cell_read(g['raw'], *cell(s)))
            if ok and got == s:
                good += 1
            else:
                badp.append((s, got, why))
        ap_ok = (good == NSLOTS)
        P('[G] allpat 盘 %s: 全 %d 槽图案解码回槽号 **%d** %s (坏 %s)'
          % (os.path.basename(a.allpat), NSLOTS, good, '✓' if ap_ok else '✗', badp[:5]))
        res['G_allpat'] = dict(decoded=good, total=NSLOTS, ok=bool(ap_ok), bad=badp[:20])

    allok = (g1 and g2 and g3 and g4 and not oob and not dup and v1max <= h
             and not bad_cells and same_plane and not n_res_ink and not live_empty
             and not r84_empty and not bad_bor and not bad
             and res.get('F2_ascii182', {}).get('pass_') is not False
             and (ap_ok is not False))
    P('')
    P('=' * 100)
    P('[结论] 图集/字形/ASCII: %s' % ('全部通过 ✓' if allok else '★有未通过项'))
    P('=' * 100)
    res['all_ok'] = bool(allok)
    res['log'] = LOG
    with io.open(os.path.join(a.out, 'rel_atlas_base.json'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    return 0 if allok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
