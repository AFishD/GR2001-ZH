# -*- coding: utf-8 -*-
r"""cap_k2_recon.py -- SKIP=2 重做前的**只读**侦察 (基底 GR_ZH124)

回答:
  ① FONT.RES 结构: IMG 条目字段 / LZO 子流表 / 展开态偏移 / 三个 face 的记录偏移
  ② 右边缘 ASCII 条带 (u0>=992) 的 63 个矩形 + 182 条引用 (**逐条**列出)
  ③ ★ 记录采样窗语义: 记录矩形原值 vs 矩形+(4,2) —— 用"墨是否被窗边切掉"实测判定
  ④ SKIP 3→2 会动到哪些记录 (旧跳过带 y194..241 的第三条 y226..241 变成网格 row12)
  ⑤ 新布局 (h=644/64 列/SKIP=2) 的格位表 + 空闲带 (row37 等)
  ⑥ FONT.RES 在 MENU.IMG 里的**槽余量** (改记录后重压是否装得下)

用法: python tools/re/toolbelt/cap_k2_recon.py [--iso <基底盘>] [--out <txt>]
"""
import argparse
import io
import os
import struct
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
H_BASE = 512
NCOL_OLD, SKIP_OLD = 62, 3
H_NEW, NCOL_NEW, SKIP_NEW = 644, 64, 2
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


def rows_fit(h, skip):
    r = 0
    while yrow(r, skip) + 16 <= h:
        r += 1
    return r


def open_font(iso_p):
    iso = T.Iso(iso_p)
    ent = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ent if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ent if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    img, cov = zx_lib.decode_engine(bytes(pak[rec[6]:rec[6] + rec[5]]), rec[2], rec[3])
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    subs = T.lzo_subs(ft_slot)
    blob = b''.join(s[0] for s in subs)
    faces, endp = zx_lib.ft_records(blob, 28)
    # 紧随其后的条目 (看槽余量)
    ordered = sorted(ent, key=lambda e: e['off'])
    nxt = None
    for k, e in enumerate(ordered):
        if e['name'] == 'FONT.RES':
            nxt = ordered[k + 1] if k + 1 < len(ordered) else None
    return dict(iso=iso, ent=ent, e_pak=e_pak, e_ft=e_ft, pak=pak, rec=rec, img=img, cov=cov,
                ft_slot=ft_slot, subs=subs, blob=blob, faces=faces, endp=endp, nxt=nxt,
                ordered=ordered)


def ink_of(plane, u0, v0, u1, v1):
    return plane[v0:v1, u0:u1]


def bbox(mask):
    if not mask.any():
        return None
    ys, xs = np.nonzero(mask)
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH124',
                                                 'GR_ZH124.iso'))
    ap.add_argument('--out', default=None)
    a = ap.parse_args(argv)
    f = open_font(a.iso)
    img = f['img']
    e_ft = f['e_ft']
    P('=' * 100)
    P('cap_k2_recon.py  iso = %s' % a.iso)
    P('[pak] COMMON.PAK off=0x%X stored=%d real=%d' % (f['e_pak']['off'], f['e_pak']['stored'],
                                                       f['e_pak']['real']))
    P('[ft ] FONT.RES  off=0x%X stored=%d real=%d ; 槽余量 = 下一条目 off 0x%X ⇒ 可用 %d B'
      % (e_ft['off'], e_ft['stored'], e_ft['real'],
         f['nxt']['off'], f['nxt']['off'] - e_ft['off'] - e_ft['stored']))
    P('[ft ] 下一条目 = %s (off=0x%X stored=%d)' % (f['nxt']['name'], f['nxt']['off'],
                                                    f['nxt']['stored']))
    P('[lzo] FONT.RES 子流 %d 个 (comp/real): %s ; 展开合计 %d B'
      % (len(f['subs']), [(s[1], s[2]) for s in f['subs']], len(f['blob'])))
    P('[lzo] 各子流在**槽内**的偏移: %s' % [(s[3], s[3] + 8, s[1]) for s in f['subs']])
    P('[ft ] 展开态: %d B ; 记录表解析终点 0x%X ; 尾部残留 %d B'
      % (len(f['blob']), f['endp'], len(f['blob']) - f['endp']))
    faces = f['faces']
    P('[ft ] 展开态前 28 B: %s' % f['blob'][:28].hex())
    off = 28
    for (nm, fld, rows) in faces:
        P('[face] %-8s @展开偏移 0x%04X  nrec=%d (fld4=%d fld5=%d)  records @0x%04X..0x%04X'
          % (nm, off, fld[4] * fld[5], fld[4], fld[5], rows[0][0], rows[-1][0] + 10))
        P('       fld14 = %s' % fld)
        off = rows[-1][0] + 10

    # ── ② 右边缘 ASCII 条带 ──
    P('')
    P('② 右边缘 ASCII 条带 (u0 >= 992) 逐条清单')
    strip = {}
    refs = []
    for (nm, fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3] and r[2] >= 992:
                strip.setdefault(r, []).append((nm, k))
                refs.append((nm, k, o, r))
    P('[strip] 不同矩形 **%d** 个 ; 引用 **%d** 条' % (len(strip), len(refs)))
    P('% -4s %-8s %-5s %-6s %-28s %-10s %-6s %-6s %-22s' %
      ('#', 'face', 'idx', 'code', 'rect(u0,v0,u1,v1)', 'wh', 'ink', 'ink+42', 'ink bbox (rect/42)'))
    for i, (r, v) in enumerate(sorted(strip.items()), 1):
        b0, b1, u0, v0, u1, v1 = r
        m = ink_of(img, u0, v0, u1, v1)
        m2 = ink_of(img, u0 + DU, v0 + DV, u1 + DU, v1 + DV)
        bb, bb2 = bbox(m), bbox(m2)
        P('%-4d %-8s %-5d 0x%02X  (%4d,%3d,%4d,%3d) %-10s %-6d %-6d %s / %s'
          % (i, '+'.join(sorted(set(n for (n, _k) in v))), v[0][1], v[0][1] + 0x20,
             u0, v0, u1, v1, '%dx%d' % (u1 - u0, v1 - v0), int(m.sum()), int(m2.sum()),
             bb, bb2))
    tot = sum((r[4] - r[2]) * (r[5] - r[3]) for r in strip)
    P('[strip] 总 texel %d (= %.1f 格) ; 尺寸分布 %s'
      % (tot, tot / 256.0,
         {k: sum(1 for r in strip if (r[4] - r[2], r[5] - r[3]) == k)
          for k in sorted({(r[4] - r[2], r[5] - r[3]) for r in strip})}))
    xs = sorted({r[2] for r in strip})
    ys = sorted({r[3] for r in strip})
    P('[strip] u0 取值 %s' % xs)
    P('[strip] v0 取值 %s' % ys)

    # ── ③ 采样窗语义判定 (逐矩形: 哪一边的墨被切掉) ──
    P('')
    P('③ 采样窗语义 (记录矩形 vs 矩形+%d/%d): 看 8x16 矩形里墨的左右边界' % (DU, DV))
    for r in sorted(strip):
        b0, b1, u0, v0, u1, v1 = r
        if (u1 - u0, v1 - v0) != (8, 16):
            continue
        m = ink_of(img, u0, v0, u1, v1)
        if not m.any():
            continue
        cols = m.any(axis=0)
        rows_ = m.any(axis=1)
        P('    u0=%4d v0=%3d 墨列 (rect 内 0..7): %s  墨行 (0..15): %s'
          % (u0, v0, ''.join('#' if c else '.' for c in cols),
             ''.join('#' if c else '.' for c in rows_)))

    # ── ④ SKIP 3→2 影响面 ──
    P('')
    P('④ SKIP 3→2 的影响面')
    P('[band] 旧跳过带 y194..241 (3 行) ⇒ 新跳过带 y194..225 (2 行); **y226..241 这一行变成网格 row12**')
    for skip, tag in ((SKIP_OLD, 'old'), (SKIP_NEW, 'new')):
        r12 = yrow(12, skip)
        P('    SKIP=%d: row11 y=%d..%d ; row12 y=%d..%d ; row13 y=%d..%d'
          % (skip, yrow(11, skip), yrow(11, skip) + 15, r12, r12 + 15,
             yrow(13, skip), yrow(13, skip) + 15))
    hit = []
    for (nm, fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            if r[4] <= r[2] or r[5] <= r[3]:
                continue
            if r[3] < 242 and r[5] > 226:
                hit.append((nm, k, o, r))
    P('[rec ] 与 y226..241 相交的非空记录 **%d** 条:' % len(hit))
    for (nm, k, o, r) in hit:
        b0, b1, u0, v0, u1, v1 = r
        m = ink_of(img, u0, v0, u1, v1)
        P('       %-8s idx=%-4d code=0x%02X rect=(%4d,%3d,%4d,%3d) ink_in_rect=%d 展开偏移=0x%X'
          % (nm, k, k + 0x20, u0, v0, u1, v1, int(m.sum()), o))
    # 旧跳过带里的记录分布
    inband = []
    for (nm, fld, rows) in faces:
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3] and 194 <= r[3] <= 241:
                inband.append((nm, k, r))
    P('[rec ] v0 落在旧跳过带 194..241 的非空记录 **%d** 条 (v1 最大 %d)'
      % (len(inband), max(r[5] for (_n, _k, r) in inband) if inband else -1))

    # ── ⑤ 新布局格位 / 空闲带 ──
    P('')
    P('⑤ 新布局 (h=%d / %d 列 / SKIP=%d)' % (H_NEW, NCOL_NEW, SKIP_NEW))
    nr = rows_fit(H_NEW, SKIP_NEW)
    P('[geom] 可达行 0..%d (%d 行) × %d 列 = %d 格 ; 槽 0..2349 用到行 0..%d'
      % (nr - 1, nr, NCOL_NEW, nr * NCOL_NEW, 2349 // NCOL_NEW))
    for row in range(nr):
        y = yrow(row, SKIP_NEW)
        s0, s1 = row * NCOL_NEW, row * NCOL_NEW + NCOL_NEW - 1
        used = '槽 %d..%d' % (s0, s1) if s0 <= 2349 else '★ 无槽 (空闲)'
        P('    row %2d  y %3d..%-3d  %s' % (row, y, y + 15, used))
    P('[geom] 槽 2345..2349 (借槽) 的新格位:')
    for s in range(2345, 2350):
        x, y = cell(s, NCOL_NEW, SKIP_NEW)
        P('        slot %d → row %d col %d → 格 (%d, %d)  [旧 SKIP=3 时 y=%d]'
          % (s, s // NCOL_NEW, s % NCOL_NEW, x, y, yrow(s // NCOL_NEW, SKIP_OLD)))
    P('[geom] 空余: 行 36 col 46..63 = 槽 2350..2367 (18 格) + 行 37 全体 (64 格) = 82 格')

    # ── ⑥ 槽余量 ──
    P('')
    P('⑥ FONT.RES 重压余量')
    slack = f['nxt']['off'] - e_ft['off'] - e_ft['stored']
    P('[slack] 当前 stored=%d ⇒ 槽 %d B ; 下一条目 %s @0x%X ⇒ **余量 %d B** (%.1f%%)'
      % (e_ft['stored'], e_ft['stored'] + slack, f['nxt']['name'], f['nxt']['off'], slack,
         100.0 * slack / e_ft['stored']))
    # 重压不变数据验证余量口径
    repacked = T.lzo_pack([(s[0], s[2]) for s in f['subs']])
    P('[slack] 用 T.lzo_pack 原样重压: %d B (原 %d B, Δ=%+d) ⇒ 本工具链的重压基线可用'
      % (len(repacked), len(f['ft_slot']), len(repacked) - len(f['ft_slot'])))
    out = a.out or os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'temp',
                                'k2_recon.txt')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with io.open(out, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    print('[out] %s' % out)
    f['iso'].close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
