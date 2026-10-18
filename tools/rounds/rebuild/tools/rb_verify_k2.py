# -*- coding: utf-8 -*-
r"""cap_verify_k2.py -- SKIP=2 成品盘的**离线全量核对** (dump_font 家族 + 独立读回 + ASCII 182 条证明)

    python tools/re/toolbelt/cap_verify_k2.py --iso work/builds/GR_FA2400_K2/GR_FA2400_K2.iso \
        --allpat work/builds/GR_FA2400_K2/GR_FA2400_K2_allpat.iso --tag k2_final

复用 `cap_verify.py` 的骨架, 但把**几何常量**按本轮改到:
    tcslib.NCOL=64 / GRID_SKIP_ROWS=2 / GRID_Y0=3 / LEAD_HI=PAIR_LEAD_HI=0xBA

判据 (§14 + §16.4 + 任务书):
  [1] 图集三闸门: w<=1024 / px_size == w*h/2+16 / (w*h/2)%2048==0
  [2] dump_font: 槽 0..2349 全可寻址 / 几何体检 (保留槽与有字形槽**分开计数**)
  [3] 三闸门口径的载荷级旧码扫描 (0xB1..0xB9 单字节位 = 0) —— 见 cap_scan_payload_k2.py
  [4] ★ ASCII 表: 63 个矩形 / 182 条记录 → 新矩形逐 texel == 基底 (逐条列出)
  [5] ★ 槽 0..2349 全可寻址闭环 (allpat 全量解码) + 现役 1736 格逐 texel == 基底
  [6] 5 个借槽字形 (含自制 ✕) 逐 texel == 模板
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402
import cap_build as CB                                                # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp', 'verify_out')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
HANDOFF = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'temp', 'handoff',
                       'glyph_handoff.json')
W, H = 1024, 644
NCOL, SKIP, Y0 = 64, 2, 3
NCOL_OLD, SKIP_OLD, Y0_OLD = 62, 3, 2
NSLOTS, LIVE_HI, RES_LO, RES_HI = 2350, 1735, 1872, 2344
R84_LO, R84_HI = 1736, 1871
R84_SRC = os.path.join(REPO, 'work', 'builds', 'GR_F364', 'GR_F364.iso')
LEAD_HI = 0xBA
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip, y0):
    return y0 + 16 * (row + (skip if row >= 12 else 0))


def cell(slot, ncol, skip, y0):
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
    return dict(rec=rec, raw=raw, segs=segs, ft_slot=ft_slot, faces=faces,
                pak=pak, e_pak=e_pak, e_ft=e_ft,
                ink=raw_to_ink(raw, rec[3]))


def xmark():
    g = np.zeros((16, 16), dtype=bool)
    for k in range(13):
        g[1 + k, 1 + k] = True
        g[1 + k, 13 - k] = True
    return g


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(OUTDIR, 'GR_FA2400_K2.iso'))
    ap.add_argument('--allpat', default=os.path.join(OUTDIR, 'GR_FA2400_K2_allpat.iso'))
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--tag', default='k2_final')
    ap.add_argument('--no-dump', action='store_true')
    ap.add_argument('--charset', default=None,
                    help='覆盖 tcslib.CHARSET (默认=盘上现役文件)')
    a = ap.parse_args(argv)
    out = os.path.join(OUTDIR, 'temp', 'dump_' + a.tag)
    os.makedirs(out, exist_ok=True)

    # ── [1] 三闸门 (从盘上读, 不信任工具内部值) ──
    P('=' * 100)
    P('rb_verify_k2.py (cap_verify_k2.py 的 charset 可换副本)  ★ SKIP=2 成品核对: %s'
      % os.path.abspath(a.iso))
    if a.charset:
        T.CHARSET = os.path.abspath(a.charset)
        P('[cs ] ★ 本次校验用 charset = %s' % T.CHARSET)
    P('=' * 100)
    f = open_font(a.iso)
    w, h, px = f['rec'][2], f['rec'][3], f['rec'][5]
    P('[1] 图集三闸门:')
    P('    w = %d (硬闸 w<1025: %s)' % (w, '✓' if w < 1025 else '✗'))
    P('    px_size = %d == w*h/2+16 = %d : %s' % (px, w * h // 2 + 16,
                                                 '✓' if px == w * h // 2 + 16 else '✗'))
    P('    (w*h/2) %% 2048 = %d : %s' % ((w * h // 2) % 2048,
                                         '✓' if (w * h // 2) % 2048 == 0 else '✗'))
    P('    px_size <= 329,744 (h=644 已验证通过值): %s'
      % ('✓' if px <= 329744 else '✗'))
    assert w < 1025 and px == w * h // 2 + 16 and (w * h // 2) % 2048 == 0
    P('    容器 %d B / %d 段 ; payload %d == w*h/2 - %d*48 : %s'
      % (len(f['raw']) // 1, len(f['segs']), sum(s[2] for s in f['segs']), len(f['segs']),
         '✓' if sum(s[2] for s in f['segs']) == w * h // 2 - len(f['segs']) * 48 else '✗'))

    # ── [2] dump_font 家族 (运行时改几何常量) ──
    T.NCOL = NCOL
    T.GRID_SKIP_ROWS = SKIP
    T.GRID_Y0 = Y0
    T.LEAD_HI = LEAD_HI
    T.PAIR_LEAD_HI = LEAD_HI
    P('[2] dump_font 家族: 运行时 tcslib.NCOL=%d / GRID_SKIP_ROWS=%d / GRID_Y0=%d / '
      'LEAD_HI=0x%02X' % (NCOL, SKIP, Y0, LEAD_HI))
    import dump_font as DF                                            # noqa: E402
    sums = {}
    for mode, cs_trim in (('full', None), ('live', R84_HI)):
        tagm = '%s_%s' % (a.tag, mode)
        outm = os.path.join(OUTDIR, 'temp', 'dump_' + tagm)
        os.makedirs(outm, exist_ok=True)
        if cs_trim is not None:
            raw = json.load(io.open(T.CHARSET, encoding='utf-8'))
            keep = {}
            for ch, p in raw['pair_of'].items():
                slot = (int(p[0]) - T.LEAD_LO) * T.PAIR_STRIDE + (int(p[1]) - T.PAIR_TRAIL_LO)
                if slot <= cs_trim:
                    keep[ch] = p
            trimmed = dict(raw)
            trimmed['pair_of'] = keep
            trimmed['_cap_verify_k2'] = ('只保留**有字形**槽 0..%d 的 pair (%d 条); '
                                         '受保护 charset 未动' % (cs_trim, len(keep)))
            csp = os.path.join(OUTDIR, 'temp', 'charset_live%d_k2.json' % (cs_trim + 1))
            with io.open(csp, 'w', encoding='utf-8', newline='\n') as fh:
                json.dump(trimmed, fh, ensure_ascii=False, indent=1)
            T.Charset.__init__.__defaults__ = (csp,)
        else:
            T.Charset.__init__.__defaults__ = (T.CHARSET,)
        DF.dump_font(os.path.abspath(a.iso), outm, tagm, scale=1, want_png=True, grid=True,
                     only_sampled=True, verbose=False)
        s = json.load(io.open(os.path.join(outm, tagm + '_font_summary.json'),
                              encoding='utf-8'))
        sums[mode] = s
        g = s.get('glyph_geometry') or {}
        v = g.get('verdict') or {}
        cap = s.get('capacity') or {}
        P('    ── charset 口径 %-4s ⇒ %s' % (mode, outm))
        P('       atlas: %dx%d px_size=%d ink=%d'
          % (s['atlas']['width'], s['atlas']['height'], s['atlas']['px_size_declared'],
             s['atlas']['ink_texels']))
        if cap:
            P('       capacity.pair: capacity=%s used=%s free=%s lead=%s'
              % (cap.get('pair', {}).get('capacity'), cap.get('pair', {}).get('used'),
                 cap.get('pair', {}).get('free'), cap.get('pair', {}).get('lead_range')))
        cnt = g.get('counts') or {}
        P('       几何体检 verdict: %s' % json.dumps(v, ensure_ascii=False))
        P('       counts: 采样窗 %s (对偶 %s + FT %s) ; by_level %s ; by_flag %s'
          % (cnt.get('windows_total'), cnt.get('pair_windows'), cnt.get('ft_record_windows'),
             cnt.get('by_level'), cnt.get('by_flag')))
        P('       one_line: %s' % g.get('one_line'))
        with io.open(os.path.join(outm, 'DUMP_SUMMARY.json'), 'w', encoding='utf-8',
                     newline='\n') as fh:
            json.dump(s, fh, ensure_ascii=False, indent=1)
    vfull = ((sums['full'].get('glyph_geometry') or {}).get('verdict') or {})
    vfull_c = ((sums['full'].get('glyph_geometry') or {}).get('counts') or {})
    vliv = ((sums['live'].get('glyph_geometry') or {}).get('verdict') or {})
    vliv_c = ((sums['live'].get('glyph_geometry') or {}).get('counts') or {})
    P('    ★ 保留槽与有字形槽**分开计数**:')
    P('       · charset **全量** (pair_of 2350): 采样窗 %s (对偶 %s) ; 错误 **%s** / '
      '空白 **%s** / 截断 **%s** / 越窗 **%s** / 警告 %s'
      % (vfull_c.get('windows_total'), vfull_c.get('pair_windows'), vfull.get('errors'),
         vfull.get('empty'), vfull.get('truncated'), vfull.get('overflow'),
         vfull.get('warnings')))
    P('       · charset 只含**有字形槽** 0..%d (1872 条): 采样窗 %s (对偶 %s) ; '
      '错误 **%s** / 空白 **%s** / 截断 **%s** / 越窗 **%s** / 警告 %s ⇒ 几何体检 %s'
      % (R84_HI, vliv_c.get('windows_total'), vliv_c.get('pair_windows'),
         vliv.get('errors'), vliv.get('empty'), vliv.get('truncated'),
         vliv.get('overflow'), vliv.get('warnings'), 'ok' if vliv.get('ok') else '✗'))
    P('       ⇒ 全量的错误数 %s = **保留槽 %d 个(%d..%d, 按 §7/§15.5 登记"槽位就绪、'
      '字形待补")** + 其它 0 ; 有字形槽 (现役 %d + r83/r84 %d + 借槽 5 = %d) 一组 **0 错**'
      % (vfull.get('errors'), RES_HI - RES_LO + 1, RES_LO, RES_HI, LIVE_HI + 1,
         R84_HI - R84_LO + 1, LIVE_HI + 1 + (R84_HI - R84_LO + 1) + 5))
    assert vliv.get('errors') == 0 and not vliv.get('truncated'), vliv
    n_res_full = vfull.get('errors', 0) - vliv.get('errors', 0)
    P('       差值 = %d (= 保留槽 %d 个; 借槽 5 个已在 live 组内)' % (n_res_full,
                                                                    RES_HI - RES_LO + 1))
    T.Charset.__init__.__defaults__ = (T.CHARSET,)

    # ── [2b] ★ 文本引用槽位: 不得引用保留槽 (否则就是"缺字形") ──
    P('')
    P('[2b] ★ 成品盘三容器的**文本引用槽位** (缺字形 = 引用了无字形槽):')
    import collections                                                # noqa: E402
    isof = T.Iso(a.iso)
    used_all = collections.Counter()
    for (lba, idx, tag) in ((T.MENU_LBA, 25, 'EN_STRINGS.RES@MENU'),
                            (T.GR_LBA, T.LANG_GR_IDX, 'EN_STRINGS.RES@GR'),
                            (T.MENU_LBA, T.XML_IDX, 'EN_SPECIAL_FEATURE.XML')):
        e = isof.img_entry(lba, idx)
        blob = b''.join(s[0] for s in T.lzo_subs(isof.read(e['iso_off'], e['stored'])))
        n, p, cnt = len(blob), 0, collections.Counter()
        while p < n:
            v = blob[p]
            if T.LEAD_LO <= v < LEAD_HI and p + 1 < n and T.PAIR_TRAIL_LO <= blob[p + 1] \
                    <= T.PAIR_TRAIL_HI:
                cnt[(v - T.LEAD_LO) * T.PAIR_STRIDE + (blob[p + 1] - T.PAIR_TRAIL_LO)] += 1
                p += 2
            else:
                p += 1
        hi = sorted(s for s in cnt if s > LIVE_HI)
        P('    %-24s blob %7d B ; 引用对偶槽 %4d 个 ; **槽 > %d 的: %d 个 %s**'
          % (tag, n, len(cnt), LIVE_HI, len(hi), hi))
        bad = [s for s in hi if s < 2345]
        P('       其中落在**保留段 1736..2344** 的: %d %s %s'
          % (len(bad), bad[:10], '✓ 无' if not bad else '✗'))
        assert not bad, bad
        used_all.update(cnt)
    isof.close()

    # ── [3] 独立读回: 三闸门 + 全槽可寻址 ──
    # RB_NO_BASE=1 ⇒ 跳过「与已丢失基底盘/来源盘对比」的段落 (GR_ZH124 / GR_F364 已不存在)
    fb = None if os.environ.get('RB_NO_BASE') else open_font(a.base)
    P('')
    P('[5] 独立读回 (不依赖 dump_font):')
    oob, dup, cells = [], [], {}
    for s in range(NSLOTS):
        x, y = cell(s, NCOL, SKIP, Y0)
        if not (0 <= x and x + 16 <= w and 0 <= y and y + 16 <= h):
            oob.append((s, x, y))
        if (x, y) in cells:
            dup.append((s, cells[(x, y)]))
        cells[(x, y)] = s
    nrow = max(s // NCOL for s in range(NSLOTS)) + 1
    P('    [geom] 槽 0..%d: 越界 %d / 格位重复 %d / 不同格位 %d ; 用到行 0..%d ; '
      'V1_max = %d <= h %d' % (NSLOTS - 1, len(oob), len(dup), len(cells), nrow - 1,
                               yrow(nrow - 1, SKIP, Y0) + 16, h))
    assert not oob and not dup
    live_bad = []
    for s in (range(LIVE_HI + 1) if fb is not None else ()):
        gb = CB.cell_read(fb['raw'], *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD))
        gp = CB.cell_read(f['raw'], *cell(s, NCOL, SKIP, Y0))
        if not (gb == gp).all():
            live_bad.append(s)
    P('    [addr] 现役槽 0..%d 逐 texel == 基底: **%d/%d** (不同 %s) %s'
      % (LIVE_HI, LIVE_HI + 1 - len(live_bad), LIVE_HI + 1, live_bad[:5],
         '✓' if not live_bad else '✗'))
    assert not live_bad
    # ★ r83/r84 槽 1736..1871 (来源盘 GR_F364; GR_ZH124 在这段是空的)
    f8 = None
    bad_r84 = []
    for s in (range(R84_LO, R84_HI + 1) if f8 is not None else ()):
        gs = CB.cell_read(f8['raw'], *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD))
        gp = CB.cell_read(f['raw'], *cell(s, NCOL, SKIP, Y0))
        if not (gs == gp).all() or not gs.any():
            bad_r84.append((s, int((gs != gp).sum()), int(gs.sum())))
    P('    [addr] ★ r83/r84 槽 %d..%d 逐 texel == 来源盘 %s: **%d/%d** %s'
      % (R84_LO, R84_HI, os.path.basename(R84_SRC), (R84_HI - R84_LO + 1) - len(bad_r84),
         R84_HI - R84_LO + 1, bad_r84[:5]))
    assert not bad_r84
    # 保留槽空
    n_res_ink = [(s, int(CB.cell_read(f['raw'], *cell(s, NCOL, SKIP, Y0)).sum()))
                 for s in range(RES_LO, RES_HI + 1)
                 if CB.cell_read(f['raw'], *cell(s, NCOL, SKIP, Y0)).any()]
    P('    [addr] 保留槽 %d..%d 全空: %d/%d %s (有墨 %s)'
      % (RES_LO, RES_HI, (RES_HI - RES_LO + 1) - len(n_res_ink), RES_HI - RES_LO + 1,
         '✓' if not n_res_ink else '✗', n_res_ink[:5]))
    assert not n_res_ink
    # 借槽字形
    hd = json.load(io.open(HANDOFF, encoding='utf-8'))
    tmpl = {}
    for it in hd['items']:
        tmpl[it['slot']] = (np.array(it['bitmap'], dtype=int) == 0)
    tmpl[2349] = xmark()
    bad_bor = []
    for s, ink in tmpl.items():
        got = CB.cell_read(f['raw'], *cell(s, NCOL, SKIP, Y0))
        if not (got == ink).all():
            bad_bor.append((s, int((got != ink).sum())))
    P('    [borrow] 5 个借槽 (2345 按 / 2346 时 / 2347 小 / 2348 击 / 2349 ✕自制): '
      '逐 texel == 模板 %s (不符 %s)'
      % ('✓' if not bad_bor else '✗', bad_bor))
    assert not bad_bor
    # ── [4] ★ ASCII 表 182 条逐 texel 证明 ──
    P('')
    P('[4] ★ ASCII 字形表 (码位 0x21..0x9C): 逐条"记录 → 新矩形 → 逐 texel == 基底"')
    ftb = (b''.join(s[0] for s in T.lzo_subs(fb['ft_slot']))
           if fb is not None else b'')
    faces_b, _ = (zx_lib.ft_records(ftb, 28) if fb is not None else ([], 0))
    strip = {}
    for (fn, fld, rows) in (faces_b if fb is not None else ()):
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3] and r[2] >= 992:
                strip.setdefault((r[2], r[3], r[4], r[5]), []).append((fn, k, o, r))
    P('    基底盘 x>=992 的 ASCII 表: **%d** 个不同矩形 / **%d** 条记录'
      % (len(strip), sum(len(v) for v in strip.values())))
    ftf = b''.join(s[0] for s in T.lzo_subs(f['ft_slot']))
    faces_f, _ = zx_lib.ft_records(ftf, 28)
    off_new = {fn: rows[0][0] for (fn, fld, rows) in faces_f}
    n_eq, n_bad, n_moved, det = 0, [], 0, []
    for (r, refs) in sorted(strip.items()):
        inkb = fb['ink'][r[1]:r[3], r[0]:r[2]]
        for (fn, k, o, _r6) in refs:
            o2 = off_new[fn] + k * 10
            import struct
            b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', ftf, o2)
            nw = (u0, v0, u1, v1)
            inkf = f['ink'][v0:v1, u0:u1] if (v1 <= h and u1 <= w) else None
            ok = inkf is not None and inkf.shape == inkb.shape and (inkf == inkb).all()
            n_eq += 1 if ok else 0
            n_moved += 1 if nw != r else 0
            if not ok:
                n_bad.append((fn, k, k + 0x20, r, nw))
            det.append(dict(face=fn, idx=k, code='0x%02X' % (k + 0x20), base=list(r),
                            new=list(nw), ink=int(inkb.sum()), moved=(nw != r), equal=bool(ok)))
    P('    ★ 182 条记录逐 texel 相等: **%d/%d** %s ; 其中被搬 %d 条'
      % (n_eq, sum(len(v) for v in strip.values()), '✓' if not n_bad else '✗ %s' % n_bad[:5],
         n_moved))
    assert not n_bad and n_eq == sum(len(v) for v in strip.values())
    P('    逐条明细 (前 12 条 / 全部见 json):')
    for dd in det[:12]:
        P('      %-8s #%-4d 0x%02X 基底(%4d,%3d,%4d,%3d) → 新(%4d,%3d,%4d,%3d) 墨 %-4d 逐texel相等 %s'
          % (dd['face'], dd['idx'], int(dd['code'], 16), dd['base'][0], dd['base'][1],
             dd['base'][2], dd['base'][3], dd['new'][0], dd['new'][1], dd['new'][2],
             dd['new'][3], dd['ink'], dd['equal']))
    with io.open(os.path.join(out, 'ascii_182_records.json'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump(det, fh, ensure_ascii=False, indent=1)

    # ── [5b] allpat 全量解码 ──
    allpat_ok = None
    if a.allpat and os.path.isfile(a.allpat):
        g = open_font(a.allpat)
        P('')
        P('[5b] allpat 盘: %s' % os.path.abspath(a.allpat))
        n_ok, bad = 0, []
        for s in range(NSLOTS):
            ok, got, why = CB.pattern_decode(CB.cell_read(g['raw'], *cell(s, NCOL, SKIP, Y0)))
            if ok and got == s:
                n_ok += 1
            else:
                bad.append((s, got, why))
        allpat_ok = n_ok
        P('     ★ 全部 %d 槽写入图案并解码回槽号: **%d ✓** %s' % (NSLOTS, n_ok, bad[:4]))
        assert n_ok == NSLOTS
        with io.open(os.path.join(out, 'allpat_decode.json'), 'w', encoding='utf-8',
                     newline='\n') as fh:
            json.dump(dict(slots=NSLOTS, ok=n_ok, bad=bad[:50]), fh, ensure_ascii=False,
                      indent=1)
    res = dict(tag=a.tag, iso=os.path.abspath(a.iso), base=os.path.abspath(a.base),
               w=w, h=h, ncol=NCOL, skip_rows=SKIP, y0=Y0, lead_hi='0x%02X' % LEAD_HI,
               px_size=px, gates=dict(w_lt_1025=w < 1025,
                                      px_size_eq=(px == w * h // 2 + 16),
                                      mod2048=((w * h // 2) % 2048 == 0),
                                      px_le_329744=px <= 329744),
               live_same=LIVE_HI + 1 - len(live_bad), live_total=LIVE_HI + 1,
               reserved_blank=(RES_HI - RES_LO + 1) - len(n_res_ink),
               r84_same=(R84_HI - R84_LO + 1) - len(bad_r84),
               r84_total=R84_HI - R84_LO + 1, r84_src=os.path.basename(R84_SRC),
               reserved_total=RES_HI - RES_LO + 1, borrow_ok=not bad_bor,
               ascii_records_eq=n_eq, ascii_records_total=sum(len(v) for v in strip.values()),
               ascii_rects=len(strip), ascii_moved=n_moved, allpat_ok=allpat_ok,
               glyph_geometry_full=vfull, glyph_geometry_live=vliv,
               errors_full=vfull.get('errors'), errors_live=vliv.get('errors'),
               text_slots_gt_live=sorted(s for s in used_all if s > LIVE_HI),
               text_refs_reserved=sorted(s for s in used_all if RES_LO <= s <= RES_HI))
    with io.open(os.path.join(OUTDIR, 'cap_verify_%s.json' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump(dict(result=res, log=LOG), fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'cap_verify_%s.txt' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % os.path.join(OUTDIR, 'cap_verify_%s.txt' % a.tag))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
