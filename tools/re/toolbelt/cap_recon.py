# -*- coding: utf-8 -*-
r"""cap_recon.py -- 只读侦察基底盘 (GR_ZH124): 图集墨量 / FT 记录带 / 现役槽 / 冲突面

    python tools/re/toolbelt/cap_recon.py [--iso <iso>]

回答构筑前必须知道的 5 个问题 (全部实测, 不猜):
  ① 基底盘 1024x512 / 62 列的**现役槽**是 0..N (哪些格真的有墨)?
  ② 3 个 face × nrec 条 FT 记录里**非空**的矩形都落在哪些 y 带 (v0/v1 直方图)?
     ⇒ 新的 64 列网格会不会压到它们?
  ③ 图集逐引擎行 (0..511) 的墨量 —— 哪些行有活内容?
  ④ 老 12px 带 / EN 带 (y>=448) 还有没有墨? 有没有记录**指着**它?
  ⑤ 换成 64 列后, 新网格行 0..36 覆盖的 y 区间, 与记录带的交叠 = ?
"""
import collections
import io
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', 'temp')
DEFAULT_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
W, H = 1024, 512
NCOL_OLD, NCOL_NEW = 62, 64
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, ncol_unused=None):
    """引擎网格: y = 2 + 16*(row + 3*[row>=12])"""
    return 2 + 16 * (row + (3 if row >= 12 else 0))


def rows_fit(h):
    r = 0
    while yrow(r) + 16 <= h:
        r += 1
    return r


def main(argv):
    iso_p = DEFAULT_ISO
    if len(argv) >= 2 and argv[0] == '--iso':
        iso_p = argv[1]
    os.makedirs(OUTDIR, exist_ok=True)
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    P('=' * 88)
    P('cap_recon.py  iso = %s' % iso_p)
    P('[img] COMMON.PAK off=0x%X stored=%d real=%d ; FONT.RES off=0x%X stored=%d real=%d'
      % (e_pak['off'], e_pak['stored'], e_pak['real'], e_ft['off'], e_ft['stored'], e_ft['real']))
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    nm, psm, w, h, clut, px_size, PX = recs[1]
    P('[pak] rec#1 %s psm=0x%02X %dx%d clut=%d px_size=0x%X (==w*h/2+16: %s) px@0x%X'
      % (nm, psm, w, h, clut, px_size, px_size == w * h // 2 + 16, PX))
    assert (w, h) == (W, H)
    ct = bytes(pak[PX:PX + px_size])
    img, cov = zx_lib.decode_engine(ct, w, h)

    # ── ③ 逐引擎行墨量 ──
    P('')
    P('③ 引擎行墨量 (0..%d), 只列非零行:' % (h - 1))
    rowink = [(y, int(img[y].sum())) for y in range(h)]
    nz = [t for t in rowink if t[1]]
    P('    非零行 **%d** / %d ; 墨 texel 合计 %d' % (len(nz), h, sum(v for _y, v in nz)))
    prev = None
    bands = []
    for (y, v) in nz:
        if prev is not None and y == prev[1] + 1:
            prev = (prev[0], y, prev[2] + v)
        else:
            if prev:
                bands.append(prev)
            prev = (y, y, v)
    if prev:
        bands.append(prev)
    for (a, b, v) in bands:
        P('    y %4d..%-4d (%2d 行) 墨 %6d' % (a, b, b - a + 1, v))

    # ── ④ FT 记录带 ──
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    exp = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, endp = zx_lib.ft_records(exp, 28)
    P('')
    P('④ FT 记录 (FONT.RES 展开 %d B, endp 0x%X):' % (len(exp), endp))
    vhist = collections.Counter()
    for (fn, fld, rows) in faces:
        nrec = fld[4] * fld[5]
        ne = [(o, r) for (o, r) in rows if r[4] > r[2] and r[5] > r[3]]
        P('    face %-8s nrec=%3d (fld4=%d fld5=%d) 非空 %3d' % (fn, nrec, fld[4], fld[5], len(ne)))
        for (o, r) in ne:
            vhist[(r[3], r[5])] += 1
    P('    v 带直方图 (v0, v1) → 条数:')
    for (k, n) in sorted(vhist.items()):
        P('      v %4d..%-4d (高 %2d) : %3d 条%s'
          % (k[0], k[1], k[1] - k[0], n, '   <<< 落在 y>=448 (旧 EN/12px 带区)' if k[0] >= 448
             else ('   <<< 与网格行同 y' if any(yrow(r) == k[0] for r in range(64)) else '')))
    rects = []
    for (fn, fld, rows) in faces:
        for (o, r) in rows:
            if r[4] > r[2] and r[5] > r[3]:
                rects.append((fn, r[2], r[3], r[4], r[5]))
    P('    非空记录矩形合计 **%d** ; v 范围 %d..%d ; u 范围 %d..%d'
      % (len(rects), min(r[2] for r in rects), max(r[4] for r in rects),
         min(r[1] for r in rects), max(r[3] for r in rects)))
    P('    ★ 有没有记录**采样到 y>=448**: %s'
      % ('有' if any(r[3] >= 448 for r in rects) else '没有'))

    # ── ① 现役槽 (62 列引擎格) ──
    P('')
    P('① 现役槽 (老布局 %d 列, h=%d ⇒ 可达行 0..%d = %d 格):'
      % (NCOL_OLD, h, rows_fit(h) - 1, rows_fit(h) * NCOL_OLD))
    live = {}
    for s in range(rows_fit(h) * NCOL_OLD):
        r, c = s // NCOL_OLD, s % NCOL_OLD
        x, y = 16 * c, yrow(r)
        n = int(img[y:y + 16, x:x + 16].sum())
        if n:
            live[s] = n
    P('    有墨的槽 **%d** 个 ; slot 范围 %d..%d ; 连续? %s'
      % (len(live), min(live), max(live), sorted(live) == list(range(min(live), max(live) + 1))))
    gaps = [s for s in range(0, max(live) + 1) if s not in live]
    P('    区间内无墨(空字形)的槽 %d 个: %s' % (len(gaps), gaps[:20]))
    P('    每行有墨槽数:' )
    per = collections.Counter(s // NCOL_OLD for s in live)
    for r in sorted(per):
        P('      old row %2d (y=%3d) : %d 个' % (r, yrow(r), per[r]))

    # ── ⑤ 新布局 (64 列) 与记录带的交叠 ──
    P('')
    P('⑤ 新布局 %d 列, h=644 ⇒ 可达行 0..%d = %d 格; 目标 2350 槽 ⇒ 行 0..%d (余 %d 格)'
      % (NCOL_NEW, rows_fit(644) - 1, rows_fit(644) * NCOL_NEW, 2349 // NCOL_NEW,
         rows_fit(644) * NCOL_NEW - 2350))
    P('    新网格行 → y 区间:')
    for r in range(rows_fit(644)):
        y = yrow(r)
        hit = [k for k in vhist if not (k[1] <= y or k[0] >= y + 16)]
        P('      row %2d y %3d..%-3d  %s' % (r, y, y + 15,
                                             ('★ 与记录带重叠: %s' % hit) if hit else ''))
    # 新区间里现役槽的搬迁落点 (老格 → 新格) 是否越界
    over = [s for s in range(2350) if yrow(s // NCOL_NEW) + 16 > 644]
    P('    新布局下越界的槽: %d %s' % (len(over), over[:5]))
    iso.close()
    p = os.path.join(OUTDIR, 'recon.txt')
    with io.open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
