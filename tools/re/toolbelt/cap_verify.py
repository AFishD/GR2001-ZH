# -*- coding: utf-8 -*-
r"""cap_verify.py -- Step 3: 探针盘离线核对 (dump_font 家族 + 独立读回)

    python tools/re/toolbelt/cap_verify.py --iso work/builds/GR_CAP2400/GR_CAP2400.iso \
        --allpat work/builds/GR_CAP2400/GR_CAP2400_allpat.iso \
        --tag h644_c64 --h 644 --ncol 64 \
        --base work/builds/GR_ZH124/GR_ZH124.iso

两路证据:
  ① **dump_font 家族** (tools/iso_build/dump_font.py, 运行时把 tcslib 的
     NCOL/LEAD_HI/PAIR_LEAD_HI 改成该盘的几何 ⇒ 它的引擎格位公式、容量、字形几何体检
     全部按**本盘**口径跑), 产物 = PNG / ft.csv / charset.csv / summary.json /
     truncation_report.{json,md};
  ② **独立读回** (本脚本自己的解析路径): 槽 0..2349 逐个
     · 引擎格在图集内、互不重复、不越界;
     · 现役槽 0..1735 的 16x16 逐 texel == 基底盘同槽;
     · 新槽 1736..2349 的 16x16 == 该槽的确定性格子图案 (解码回槽号);
     · allpat 盘上**全部 2350 槽**都按图案解码回槽号 (写入/寻址闭环)。
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
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row):
    return 2 + 16 * (row + (3 if row >= 12 else 0))


def cell(slot, ncol):
    return 16 * (slot % ncol), yrow(slot // ncol)


def container_to_plane(cont, w, h):
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


def cell_read(plane, x, y, w=1024):
    stride = w // 2
    o = x // 2
    g = np.zeros((16, 16), dtype=bool)
    for i in range(16):
        r = plane[(y + i) * stride + o:(y + i) * stride + o + 8]
        g[i, 0::2] = [(b & 0x0F) == 0 for b in r]
        g[i, 1::2] = [(b >> 4) == 0 for b in r]
    return g


def pattern_decode(g, lo, hi):
    if not g[0, :].all() or not g[13, :].all():
        return False, -1, '上下边框不是全墨'
    if not g[:, 0].all() or not g[:, 15].all():
        return False, -1, '左右边框不是全墨'
    if list(g[14, 2:15:2]) != [True] * 7 or any(g[14, x] for x in (1, 3, 5, 7, 9, 11, 13)):
        return False, -1, '同步字 A 不符'
    if list(g[15, 1:14:2]) != [True] * 7 or any(g[15, x] for x in (2, 4, 6, 8, 10, 12, 14)):
        return False, -1, '同步字 B 不符'
    slot = 0
    for k in range(12):
        seg = g[1 + k, 2:14]
        if seg.all():
            slot |= (1 << k)
        elif seg.any():
            return False, -1, 'row%d 数据位非全墨/全空' % (1 + k)
    if not (lo <= slot <= hi):
        return False, slot, '槽号超界'
    return True, slot, ''


def open_font(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    cont = bytes(pak[rec[6]:rec[6] + rec[5]])
    plane, segs = container_to_plane(cont, rec[2], rec[3])
    iso.close()
    return dict(entry=e_pak, ft=e_ft, rec=rec, cont=cont, plane=plane, segs=segs, pak=pak)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--allpat', default=None)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--h', type=int, required=True)
    ap.add_argument('--ncol', type=int, required=True)
    ap.add_argument('--nslots', type=int, default=2350)
    ap.add_argument('--live-hi', type=int, default=1735)
    ap.add_argument('--base', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH124',
                                                   'GR_ZH124.iso'))
    ap.add_argument('--out', default=None)
    ap.add_argument('--no-dump', action='store_true')
    ap.add_argument('--lead-hi', type=lambda s: int(s, 0), default=0xBA)
    ap.add_argument('--charset-live-only', action='store_true',
                    help='把 charset 裁到**只含现役槽 0..live-hi** 的 pair 再做几何体检 '
                         '(探针盘在 live-hi+1.. 放的是测试图案, 用全量 charset 必然报"与模板不符")')
    a = ap.parse_args(argv)
    out = a.out or os.path.join(OUTDIR, 'temp', 'dump_' + a.tag)
    os.makedirs(out, exist_ok=True)

    # ── ① 让 dump_font 家族按本盘几何跑 ──
    T.NCOL = a.ncol
    T.LEAD_HI = a.lead_hi
    T.PAIR_LEAD_HI = a.lead_hi
    if a.charset_live_only:
        cs_p = os.path.join(OUTDIR, 'temp', 'charset_live%d.json' % (a.live_hi + 1))
        raw = json.load(io.open(T.CHARSET, encoding='utf-8'))
        keep = {}
        for ch, p in raw['pair_of'].items():
            slot = (int(p[0]) - T.LEAD_LO) * T.PAIR_STRIDE + (int(p[1]) - T.PAIR_TRAIL_LO)
            if slot <= a.live_hi:
                keep[ch] = p
        trimmed = dict(raw)
        trimmed['pair_of'] = keep
        trimmed['_cap_verify_trim'] = ('只保留现役槽 0..%d 的 pair (%d 条) —— 供探针盘几何体检用; '
                                       '受保护路径 charset_compiled_zh16.json 未被改动'
                                       % (a.live_hi, len(keep)))
        with io.open(cs_p, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(trimmed, f, ensure_ascii=False, indent=1)
        # ★ tcslib.Charset.__init__ 的 path 是**默认参数**(定义时就绑定了) ⇒ 必须改 __defaults__
        T.Charset.__init__.__defaults__ = (cs_p,)
        P('[charset] 几何体检用裁剪 charset: %s (pair_of %d → %d) —— 只影响本次 dump; '
          '受保护路径未动' % (cs_p, len(raw['pair_of']), len(keep)))
    import dump_font as DF                                            # noqa: E402
    geom = None
    if not a.no_dump:
        P('=' * 92)
        P('① dump_font 家族 (运行时 tcslib.NCOL=%d, LEAD_HI=0x%02X) —— 产物 %s'
          % (a.ncol, T.LEAD_HI, out))
        P('=' * 92)
        DF.dump_font(os.path.abspath(a.iso), out, a.tag, scale=1, want_png=True,
                     grid=True, only_sampled=True, verbose=False)
        summ = json.load(io.open(os.path.join(out, a.tag + '_font_summary.json'), encoding='utf-8'))
        geom = summ.get('glyph_geometry')
        capr = summ.get('capacity') or summ.get('capacity_report') or {}
        P('[dump] summary.json 关键段:')
        for k in ('atlas', 'faces', 'capacity', 'charset', 'verdict', 'glyph_geometry',
                  'selfcheck', 'icons'):
            if k in summ:
                v = summ[k]
                P('   %-16s %s' % (k, json.dumps(v, ensure_ascii=False)[:600]
                                   if not isinstance(v, str) else v[:600]))
        if geom:
            P('[dump] ★ 字形几何体检: %s' % json.dumps(geom.get('verdict'),
                                                       ensure_ascii=False))
            for f in geom.get('findings', [])[:8]:
                P('       finding: %s' % json.dumps(f, ensure_ascii=False)[:300])
        notes = summ.get('notes') or []
        P('[dump] notes (%d): %s' % (len(notes), json.dumps(notes, ensure_ascii=False)[:900]))
        with io.open(os.path.join(out, 'DUMP_SUMMARY.json'), 'w', encoding='utf-8',
                     newline='\n') as f:
            json.dump(summ, f, ensure_ascii=False, indent=1)

    # ── ② 独立读回 ──
    P('')
    P('=' * 92)
    P('② 独立读回: 槽 0..%d (h=%d, %d 列)' % (a.nslots - 1, a.h, a.ncol))
    P('=' * 92)
    f = open_font(a.iso)
    w, h, px = f['rec'][2], f['rec'][3], f['rec'][5]
    P('[probe] %s' % os.path.abspath(a.iso))
    P('[probe] rec#1 %dx%d psm=0x%02X px_size=0x%X ; 容器 %d B / %d 段 ; payload %d'
      % (w, h, f['rec'][1], px, len(f['cont']), len(f['segs']), sum(s[2] for s in f['segs'])))
    assert (w, h) == (1024, a.h) and px == w * h // 2 + 16
    assert (w * h // 2) % 2048 == 0
    P('[probe] 不变式②: px_size == w*h/2+16 ✓ ; (w*h/2)%%2048 = 0 ✓')
    oob, dup, cells = [], [], {}
    for s in range(a.nslots):
        x, y = cell(s, a.ncol)
        if not (0 <= x and x + 16 <= w and 0 <= y and y + 16 <= h):
            oob.append((s, x, y))
        if (x, y) in cells:
            dup.append((s, cells[(x, y)]))
        cells[(x, y)] = s
    P('[geom] 槽 0..%d: 越界 **%d** ; 格位重复 **%d** ; 不同格位 **%d**'
      % (a.nslots - 1, len(oob), len(dup), len(cells)))
    assert not oob and not dup
    nrow = (max(s // a.ncol for s in range(a.nslots)) + 1)
    P('[geom] 用到的网格行 0..%d ; 行 0..%d 的 y 区间全部 ≤ h-16=%d ; 余 %d 格'
      % (nrow - 1, nrow - 1, h - 16, nrow * a.ncol - a.nslots))
    # 基底盘现役字形
    fb = open_font(a.base)
    live_bad = 0
    for s in range(a.live_hi + 1):
        gb = cell_read(fb['plane'], *cell(s, 62))
        gp = cell_read(f['plane'], *cell(s, a.ncol))
        if not (gb == gp).all():
            live_bad += 1
    P('[addr] 现役槽 0..%d 逐 texel == 基底盘同槽: **%d/%d 相同** (不同 %d) %s'
      % (a.live_hi, a.live_hi + 1 - live_bad, a.live_hi + 1, live_bad,
         '✓' if live_bad == 0 else '✗'))
    pat_ok, pat_bad = 0, []
    for s in range(a.live_hi + 1, a.nslots):
        ok, got, why = pattern_decode(cell_read(f['plane'], *cell(s, a.ncol)),
                                      a.live_hi + 1, a.nslots - 1)
        if ok and got == s:
            pat_ok += 1
        else:
            pat_bad.append((s, got, why))
    P('[addr] 新槽 %d..%d 图案解码 == 槽号: **%d/%d** %s %s'
      % (a.live_hi + 1, a.nslots - 1, pat_ok, a.nslots - 1 - a.live_hi,
         '✓' if not pat_bad else '✗', pat_bad[:4]))
    P('[addr] ⇒ 槽 0..%d **全部可寻址** (现役 = 字形逐 texel 一致 / 新增 = 图案可解码) %s'
      % (a.nslots - 1, '✓' if live_bad == 0 and not pat_bad else '✗'))
    allpat_ok = None
    if a.allpat:
        g = open_font(a.allpat)
        P('[allpat] %s' % os.path.abspath(a.allpat))
        n_ok, bad = 0, []
        for s in range(a.nslots):
            ok, got, why = pattern_decode(cell_read(g['plane'], *cell(s, a.ncol)), 0, a.nslots - 1)
            if ok and got == s:
                n_ok += 1
            else:
                bad.append((s, got, why))
        allpat_ok = n_ok
        P('[allpat] **全部 %d 个槽**写入图案并解码回槽号: %d ✓ %s'
          % (a.nslots, n_ok, bad[:4]))
        assert n_ok == a.nslots
    res = dict(tag=a.tag, iso=os.path.abspath(a.iso), h=a.h, ncol=a.ncol, nslots=a.nslots,
               live_hi=a.live_hi, oob=len(oob), dup=len(dup), distinct_cells=len(cells),
               live_same=a.live_hi + 1 - live_bad, pattern_ok=pat_ok,
               addressable_all=(live_bad == 0 and not pat_bad),
               allpat_ok=allpat_ok,
               geometry_verdict=(geom or {}).get('verdict'),
               dump_dir=os.path.relpath(out, REPO).replace('\\', '/'))
    with io.open(os.path.join(OUTDIR, 'cap_verify_%s.json' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as fp:
        json.dump(dict(result=res, log=LOG), fp, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'cap_verify_%s.txt' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as fp:
        fp.write('\n'.join(LOG) + '\n')
    print('[out] %s' % os.path.join(OUTDIR, 'cap_verify_%s.txt' % a.tag))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
