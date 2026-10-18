# -*- coding: utf-8 -*-
r"""cap_build_k2.py -- ★ SKIP=2 重做 (LEAD_CAPACITY_2400.md §16.1 / §16.4 的执行)

    python tools/re/toolbelt/cap_build_k2.py --dry-run     # 只算不写 (全部断言照跑)
    python tools/re/toolbelt/cap_build_k2.py               # 真造盘 (geom + allpat)

在 `_stage644.iso` (h=644, 由 thr_patch_atlas 从 GR_ZH124 只加高) 上做:

  ① 图集重排 62 列/SKIP=3 → **64 列/SKIP=2**
       · 现役 1,736 个汉字格: 逐 texel 搬到新格 (格内容不变)
       · 槽 1736..1871 (**136 个 r83/r84 真字形**): 从 GR_F364 逐 texel 恢复
       · 槽 1872..2344 (**473 个保留槽**): 留空 (0x11), 报告里登记"无字形"
       · 槽 2345..2349 (5 个借槽): 击/小/时/按 = glyph_handoff.json 的 bitmap;
         2349 '✕' = **自制 16x16** (盘上无现成 ✕/×/X 字形; 见 temp/k2_glyphchk.txt)
  ② ★ ASCII 字形表 (x>=992 的 63 个矩形 / 182 条记录, 码位 0x21..0x9C) 的**安置**:
       64 列后网格第 62/63 列必压到它 ⇒ 逐矩形判定"窗内含现役格墨"的记录, 连同跳过带里
       被 grid row12 (y=226..241) 压到的记录, 一起搬到下方空地:
         货架 A = y 610..625, x 736..1023 (row36 的 18 个"无槽"格)
         货架 B = y 626..641, x 0..1023   (row37 整行 = SKIP 3→2 让出来的那一行)
       逐矩形: 新窗像素 **逐 texel == 旧窗**; 旧矩形清零
  ③ FONT.RES: 被搬记录的 u0/v0/u1/v1 改写 (rec[0]/rec[1] 不动) + LZO 重压回槽 (尾部补零)
  ④ ELF **6 个字节**: COLS 62→64 (1B) + SKIP_ROWS 3→2 (1B) + GATE 0xB4→0xBA (4B)

硬断言 (违反即中止):
  [A1] 现役 1,736 格在新布局逐 texel == 基底
  [A2] 473 个保留槽全空 ; 136 个 r83/r84 槽 == 来源盘 ; 5 个借槽 == handoff/自制模板
  [A3] ★ 每条非空 FT 记录: 新窗像素 == 基底同记录窗像素 (逐 texel; 含 63 个 ASCII 矩形)
  [A4] ★ 每条非空 FT 记录窗**不再含任何现役格墨** (污染 0)
  [A5] 无主墨 = 0 (新盘上每一块墨都归属某个窗/现役格/借槽)
  [A6] 64 列/SKIP=2 的 2350 个格位互不重复、不越界
  [A7] 容器回环 / PAK 容器外零改动 / FONT.RES 重压回环 / 全盘差异窗口外 0
"""
import argparse
import io
import json
import os
import shutil
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
import cap_build as CB                                                # noqa: E402  (复用)

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
STAGE = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', '_stage644.iso')
HANDOFF = os.path.join(REPO, 'work', 'builds', 'GR_TXMIG', 'temp', 'handoff',
                       'glyph_handoff.json')
R84_SRC = os.path.join(REPO, 'work', 'builds', 'GR_F364', 'GR_F364.iso')
W, H, H_OLD = 1024, 644, 512
NCOL_OLD, SKIP_OLD, Y0_OLD = 62, 3, 2
NCOL_NEW, SKIP_NEW, Y0_NEW = 64, 2, 3
SLOT_LO, SLOT_HI = 0, 2349
LIVE_HI = 1735                              # 现役 (GR_ZH124 有墨)
R84_LO, R84_HI = 1736, 1871                 # ★ r83/r84 已落盘的字 (GR_F364 有墨; GR_ZH124 无)
RES_LO, RES_HI = 1872, 2344                 # 保留槽 (空; 字形待补)
ELF_GATE = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
ELF_COLS, ELF_SKIP = 0x4170AC, 0x4170E8
ELF_Y0, ELF_V1 = 0x4170F8, 0x4170FC
GATE_OLD, GATE_NEW = 0xB4, 0xBA
VA2ISO = lambda va: va - 0x6C780            # noqa: E731
MENU_BASE = zx_lib.MENU_LBA * 2048
EMPTY_NIB = 0x1
#   货架 = 16 行高、无现役槽覆盖的整块空地 (Y0=3 ⇒ row36 y611..626 / row37 y627..642)
SHELF_A = (736, 1024, 611)                  # row36 col46..63 (槽 2350..2367 无槽)
SHELF_B = (0, 1024, 627)                    # row37 整行 (SKIP=2 让出来的第 38 行)
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def yrow(row, skip, y0=Y0_NEW):
    return y0 + 16 * (row + (skip if row >= 12 else 0))


def cell(slot, ncol, skip, y0=Y0_NEW):
    return 16 * (slot % ncol), yrow(slot // ncol, skip, y0)


def rows_fit(h, skip, y0=Y0_NEW):
    r = 0
    while yrow(r, skip, y0) + 16 <= h:
        r += 1
    return r


def raw_to_ink(raw, h, w=W):
    """nibble 平面 (bytes) → bool 墨掩码 (True = 墨, nibble==0)。"""
    stride = w // 2
    a = np.frombuffer(bytes(raw[:stride * h]), dtype=np.uint8).reshape(h, stride)
    out = np.zeros((h, w), dtype=bool)
    out[:, 0::2] = (a & 0x0F) == 0
    out[:, 1::2] = (a >> 4) == 0
    return out


def xmark():
    """★ 自制 16x16 ✕: 13x13 画框 (row/col 1..13), 两条 45° 1px 对角线, 墨 25 texel。

    与 r84 手绘 △ (slot 1504: row1..13 / col1..13 / 墨 35, temp/k2_glyphchk.txt) 同一个
    画框、同一线宽; 二值口径 (墨/背景), 原点 = 格左上角。
    """
    g = np.zeros((16, 16), dtype=bool)
    for k in range(13):
        g[1 + k, 1 + k] = True
        g[1 + k, 13 - k] = True
    return g


def rect_clear(plane, r, w=W):
    u0, v0, u1, v1 = r
    stride = w // 2
    for y in range(v0, v1):
        base = y * stride
        for x in range(u0, u1):
            o = base + x // 2
            cur = plane[o]
            plane[o] = ((cur & 0x0F) | (EMPTY_NIB << 4)) if (x & 1) else \
                ((cur & 0xF0) | EMPTY_NIB)


def rect_write_ink(plane, r, ink, w=W):
    u0, v0, u1, v1 = r
    assert ink.shape == (v1 - v0, u1 - u0), (r, ink.shape)
    stride = w // 2
    for i, y in enumerate(range(v0, v1)):
        base = y * stride
        for j, x in enumerate(range(u0, u1)):
            v = 0 if ink[i, j] else EMPTY_NIB
            o = base + x // 2
            cur = plane[o]
            plane[o] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--stage', default=STAGE)
    ap.add_argument('--out', default=os.path.join(OUTDIR, 'GR_FA2400_K2_geom.iso'))
    ap.add_argument('--allpat-out', default=os.path.join(OUTDIR, 'GR_FA2400_K2_allpat.iso'))
    ap.add_argument('--handoff', default=HANDOFF)
    ap.add_argument('--r84-from', default=R84_SRC,
                    help='★ 槽 %d..%d 的 r83/r84 字形来源盘 (GR_ZH124 无墨; GR_F364 有墨 %d 个)'
                         % (R84_LO, R84_HI, R84_HI - R84_LO + 1))
    ap.add_argument('--tag', default='k2')
    ap.add_argument('--keep-gate', action='store_true',
                    help='★ 单变量对照: **不**改 GATE (保持基底 0xB4), 其余几何照改 —— '
                         '用来把"实拍差异"归因到几何还是闸门')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    os.makedirs(OUTDIR, exist_ok=True)
    P('=' * 100)
    P('cap_build_k2.py  ★ SKIP=2 重做: h=%d / %d 列 / SKIP=%d / GATE 0x%02X / 槽 %d..%d'
      % (H, NCOL_NEW, SKIP_NEW, GATE_NEW, SLOT_LO, SLOT_HI))
    P('  base  = %s' % a.base)
    P('  stage = %s' % a.stage)
    P('  out   = %s' % a.out)
    P('=' * 100)

    # ── ⓪ 基底盘 (GR_ZH124) ──
    ib = T.Iso(a.base)
    eb = zx_lib.entries(ib, zx_lib.MENU_LBA)
    e_pak_b = [e for e in eb if e['name'] == 'COMMON.PAK'][0]
    e_ft_b = [e for e in eb if e['name'] == 'FONT.RES'][0]
    pak_b = bytes(ib.read(e_pak_b['iso_off'], e_pak_b['stored']))
    rb = T.parse_pak_records(pak_b)
    assert (rb[1][2], rb[1][3]) == (W, H_OLD)
    raw_base, _seg_b = CB.container_to_plane(bytes(pak_b[rb[1][6]:rb[1][6] + rb[1][5]]),
                                             W, H_OLD)
    ink_base = raw_to_ink(raw_base, H_OLD)
    ft_slot_b = bytes(ib.read(e_ft_b['iso_off'], e_ft_b['stored']))
    subs_b = T.lzo_subs(ft_slot_b)
    assert len(subs_b) == 1, 'FONT.RES 不是单帧'
    ft_blob_b = subs_b[0][0]
    faces_b, ft_end = zx_lib.ft_records(ft_blob_b, 28)
    recs = []
    for (fn, fld, rows) in faces_b:
        for k, (o, r) in enumerate(rows):
            if r[4] > r[2] and r[5] > r[3]:
                recs.append((fn, k, o, r))
    P('[base] PAK %d B ; 容器 %d B ; FONT.RES 槽 %d B (帧 %d / 展开 %d) ; 非空记录 **%d** 条'
      % (len(pak_b), rb[1][5], len(ft_slot_b), 8 + subs_b[0][1], len(ft_blob_b), len(recs)))
    P('[base] 基底墨 %d texel ; 现役槽 0..%d' % (int(ink_base.sum()), LIVE_HI))
    assert len(recs) == 544, len(recs)

    # ── ① stage 盘 (h=644) ──
    ist = T.Iso(a.stage)
    est = zx_lib.entries(ist, zx_lib.MENU_LBA)
    e_pak_s = [e for e in est if e['name'] == 'COMMON.PAK'][0]
    e_ft_s = [e for e in est if e['name'] == 'FONT.RES'][0]
    hdr_s = zx_lib.header(ist, zx_lib.MENU_LBA)
    names_s = zx_lib.names_region(ist, zx_lib.MENU_LBA)
    hash_s = zx_lib.hash_region(ist, zx_lib.MENU_LBA)
    assert e_pak_s['stored'] == e_pak_s['real'], '不变式①: stored != real'
    pak_s = bytes(ist.read(e_pak_s['iso_off'], e_pak_s['stored']))
    rs = T.parse_pak_records(pak_s)
    nm_s, psm_s, w_s, h_s, clut_s, px_s, PX_s = rs[1]
    assert (nm_s, psm_s, w_s, h_s) == ('new_font_revised', 0x14, W, H), rs[1]
    assert px_s == W * H // 2 + 16 and (W * H // 2) % 2048 == 0
    ct_stage = bytes(pak_s[PX_s:PX_s + px_s])
    raw_stage, segs_new = CB.container_to_plane(ct_stage, W, H)
    payload = sum(s[2] for s in segs_new)
    assert payload == W * H // 2 - len(segs_new) * 48
    ink_stage = raw_to_ink(raw_stage, H)
    assert (ink_stage[:H_OLD] == ink_base).all(), 'stage 旧 512 行 != 基底'
    P('[stage] PAK %d B ; rec#1 %dx%d px_size=0x%X ; 容器 %d B / %d 段 / payload %d ; '
      '旧 %d 行 == 基底 ✓' % (len(pak_s), w_s, h_s, px_s, len(ct_stage), len(segs_new),
                             payload, H_OLD))
    assert bytes(ist.read(e_ft_s['iso_off'], e_ft_s['stored'])) == ft_slot_b, \
        'stage 的 FONT.RES != 基底'

    # ── ② 几何 ──
    nrow = rows_fit(H, SKIP_NEW)
    cells = {}
    for s in range(SLOT_LO, SLOT_HI + 1):
        x, y = cell(s, NCOL_NEW, SKIP_NEW)
        assert 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= H, (s, x, y)
        assert (x, y) not in cells, '格位重复 %d/%d' % (s, cells[(x, y)])
        cells[(x, y)] = s
    P('[geom] h=%d / %d 列 / SKIP=%d ⇒ 可行行 0..%d (%d 行, %d 格) ; 槽 %d..%d 占行 0..%d '
      '(余 %d 格)' % (H, NCOL_NEW, SKIP_NEW, nrow - 1, nrow, nrow * NCOL_NEW, SLOT_LO,
                      SLOT_HI, SLOT_HI // NCOL_NEW, nrow * NCOL_NEW - SLOT_HI - 1))
    P('[geom] 货架 A = x%d..%d y%d..%d (槽 2350..2367 无槽) ; 货架 B = x%d..%d y%d..%d '
      '(row37 整行)' % (SHELF_A[0], SHELF_A[1] - 1, SHELF_A[2], SHELF_A[2] + 15,
                        SHELF_B[0], SHELF_B[1] - 1, SHELF_B[2], SHELF_B[2] + 15))
    P('[geom] [A6] 槽 0..2349 全部映射到互不重复、图集内的 16x16 格 ✓ (%d 格)' % len(cells))

    # ── ③ 借槽字形 (handoff 逐 texel 核对) ──
    hd = json.load(io.open(a.handoff, encoding='utf-8'))
    borrow_ink = {}
    for it in hd['items']:
        slot = it['slot']
        bm = np.array(it['bitmap'], dtype=int)
        u0, v0, u1, v1 = it['record'][2:6]
        base_ink = ink_base[v0:v1, u0:u1]
        assert bm.shape == base_ink.shape, (slot, bm.shape, base_ink.shape)
        assert ((bm == 0) == base_ink).all(), \
            'handoff slot %d 的 bitmap 与基底记录窗不逐 texel 相等' % slot
        borrow_ink[slot] = (bm == 0)
        P('[borrow] slot %d (%s, 码 %s) ← handoff bitmap %dx%d 墨 %d ; 与基底记录 '
          '(%d,%d,%d,%d) **逐 texel 相等** ✓'
          % (slot, it['char'], it['code'], bm.shape[1], bm.shape[0], int((bm == 0).sum()),
             u0, v0, u1, v1))
    assert set(borrow_ink) == {2345, 2346, 2347, 2348, 2349}, sorted(borrow_ink)
    xg = xmark()
    borrow_ink[2349] = xg
    P('[borrow] ★ slot 2349 (✕) = **自制** 16x16: 画框 row1..13 / col1..13, 两条 45° 1px '
      '对角线, 墨 **%d** texel (盘上无现成 ✕/×/X ⇒ §15.2 要求自制)' % int(xg.sum()))

    # ── ③b ★ r83/r84 槽 1736..1871 的真字形 (GR_ZH124 上没有; 从 GR_F364 取, 逐 texel 相等) ──
    ir8 = T.Iso(a.r84_from)
    er8 = zx_lib.entries(ir8, zx_lib.MENU_LBA)
    e_pak_8 = [e for e in er8 if e['name'] == 'COMMON.PAK'][0]
    pak8 = bytes(ir8.read(e_pak_8['iso_off'], e_pak_8['stored']))
    r8 = [r for r in T.parse_pak_records(pak8) if r[0] == 'new_font_revised'][0]
    raw8, _s8 = CB.container_to_plane(bytes(pak8[r8[6]:r8[6] + r8[5]]), r8[2], r8[3])
    raw124 = raw_base
    same0 = sum(1 for s in range(LIVE_HI + 1)
                if (CB.cell_read(raw8, *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD))
                    == CB.cell_read(raw124, *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD))).all())
    P('[r84 ] 来源盘 %s (%dx%d): 槽 0..%d 与基底逐 texel 相同 **%d/%d** %s'
      % (os.path.basename(a.r84_from), r8[2], r8[3], LIVE_HI, same0, LIVE_HI + 1,
         '✓' if same0 == LIVE_HI + 1 else '✗'))
    assert same0 == LIVE_HI + 1, 'r84 来源盘的现役槽与基底不一致'
    r84_ink = {}
    for s in range(R84_LO, R84_HI + 1):
        g = CB.cell_read(raw8, *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD))
        assert g.any(), '来源盘槽 %d 无墨' % s
        r84_ink[s] = g
    P('[r84 ] ★ 恢复槽 %d..%d 的真字形 **%d 个** (墨 %d..%d) —— §7 的 "r83(232)+r84(136) '
      '已落盘的字, 逐 texel 不变"; GR_ZH124 在这段是空的'
      % (R84_LO, R84_HI, len(r84_ink),
         min(int(g.sum()) for g in r84_ink.values()),
         max(int(g.sum()) for g in r84_ink.values())))
    ir8.close()

    # ── ④ 污染判定: 记录窗 ∩ 新布局"现役格墨" ──
    #   ★ 记录是 6 元组 (b0,b1,u0,v0,u1,v1); 一律按 **4 元组 (u0,v0,u1,v1)** 归类
    used_ink = np.zeros((H, W), dtype=bool)
    for s in range(LIVE_HI + 1):
        x, y = cell(s, NCOL_NEW, SKIP_NEW)
        xs, ys = cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD)
        used_ink[y:y + 16, x:x + 16] = ink_base[ys:ys + 16, xs:xs + 16]
    distinct = {}                                   # (u0,v0,u1,v1) -> [(face, idx, off, b0, b1)]
    for (fn, k, o, r) in recs:
        distinct.setdefault((r[2], r[3], r[4], r[5]), []).append((fn, k, o, r[0], r[1]))
    polluted, clean = {}, []
    for r, refs in distinct.items():
        n = int(used_ink[r[1]:r[3], r[0]:r[2]].sum())
        if n:
            polluted[r] = n
        else:
            clean.append(r)
    P('[strip] ★ 被新网格墨污染的**不同矩形 %d 个** (引用 %d 条记录) ; 干净矩形 %d 个 ; '
      '全部 %d 个' % (len(polluted), sum(len(distinct[r]) for r in polluted), len(clean),
                     len(distinct)))
    sizes = {}
    for r in polluted:
        sizes[(r[2] - r[0], r[3] - r[1])] = sizes.get((r[2] - r[0], r[3] - r[1]), 0) + 1
    need = sum(w * n for (w, _h), n in sizes.items())
    P('[strip] 尺寸分布 %s ; 需要货架宽度 %d px ; 可用 %d px'
      % (sizes, need, (SHELF_A[1] - SHELF_A[0]) + (SHELF_B[1] - SHELF_B[0])))
    # 右边缘条带里必须有"干净"矩形时也不许整块清零 —— 由上面的 keep 掩码处理
    for r in clean:
        if r[0] >= 992 and r[1] < 288:
            P('[strip] 干净矩形(保留原位): (%d,%d,%d,%d) %dx%d'
              % (r[0], r[1], r[2], r[3], r[2] - r[0], r[3] - r[1]))

    # ── ⑤ 货架装箱 (宽降序; 先 A 后 B) ──
    move = {}
    cx, cy = SHELF_A[0], SHELF_A[2]
    for r in sorted(polluted, key=lambda r: (-(r[2] - r[0]), r[1], r[0])):
        wdt = r[2] - r[0]
        if cx + wdt > SHELF_A[1]:
            cx, cy = SHELF_B[0], SHELF_B[2]
        assert cx + wdt <= SHELF_B[1], '货架装不下 %s' % (r,)
        nw = (cx, cy, cx + wdt, cy + 16)
        for s in range(SLOT_LO, SLOT_HI + 1):
            x, y = cell(s, NCOL_NEW, SKIP_NEW)
            assert not (nw[0] < x + 16 and x < nw[2] and nw[1] < y + 16 and y < nw[3]), \
                ('新窗压在现役格上', r, nw, s)
        move[r] = nw
        cx += wdt
    P('[move] ★ 搬迁表 %d 个不同矩形 → 新窗全部落在货架内、不与任何现役格相交 ✓' % len(move))
    P('[move] 货架用量: A %d px + B %d px = %d px (需要 %d px) ; 余 %d px'
      % (sum(move[r][2] - move[r][0] for r in move if move[r][1] == SHELF_A[2]),
         sum(move[r][2] - move[r][0] for r in move if move[r][1] == SHELF_B[2]),
         sum(move[r][2] - move[r][0] for r in move), need,
         (SHELF_A[1] - SHELF_A[0]) + (SHELF_B[1] - SHELF_B[0]) - need))
    for r in polluted:
        u0, v0, u1, v1 = r
        for kr in clean:
            a0, b0, a1, b1 = kr
            if u0 < a1 and a0 < u1 and v0 < b1 and b0 < v1:
                ov = ink_base[max(v0, b0):min(v1, b1), max(u0, a0):min(u1, a1)]
                assert not ov.any(), ('源矩形与干净矩形相交且有墨', r, kr, int(ov.sum()))
    P('[move] 源矩形 ∩ 干净矩形 = 只在零墨处 ✓ (清零不会伤到别的字形)')

    # ── ⑥ 新平面 ──
    plane_new = bytearray(raw_stage)
    for r, nw in move.items():
        ink = ink_base[r[1]:r[3], r[0]:r[2]].copy()
        rect_write_ink(plane_new, nw, ink)
        rect_clear(plane_new, r)
    # 右边缘条带 (x>=992, y<288) 的残余清零 —— ★ **保留**"干净矩形"的区域
    #   (有 4 个 8x16 矩形落在 y=208..223 的跳过带里, 本来就不被网格压到 ⇒ 必须原样活着)
    keep = np.zeros((288, 32), dtype=bool)
    for r in clean:
        a0, b0, a1, b1 = r
        x0, x1 = max(a0, 992), min(a1, 1024)
        y0, y1 = max(b0, 0), min(b1, 288)
        if x0 < x1 and y0 < y1:
            keep[y0:y1, x0 - 992:x1 - 992] = True
    n_clear = 0
    stride = W // 2
    for y in range(0, 288):
        for x in range(992, 1024):
            if keep[y, x - 992]:
                continue
            o = y * stride + x // 2
            cur = plane_new[o]
            nv = ((cur & 0x0F) | (EMPTY_NIB << 4)) if (x & 1) else ((cur & 0xF0) | EMPTY_NIB)
            if nv != cur:
                n_clear += 1
            plane_new[o] = nv
    P('[pix ] 右边缘条带 (x>=992, y<288) 清零: 改动 %d 个 texel ; 保留 %d 个"干净矩形"'
      % (n_clear, sum(1 for r in clean if r[0] >= 992 and r[1] < 288)))
    blank = np.zeros((16, 16), dtype=bool)
    saved = {s: CB.cell_read(raw_base, *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD))
             for s in range(LIVE_HI + 1)}
    for s in range(LIVE_HI + 1):
        CB.cell_write(plane_new, *cell(s, NCOL_OLD, SKIP_OLD, Y0_OLD), blank)
    for s in range(LIVE_HI + 1):
        CB.cell_write(plane_new, *cell(s, NCOL_NEW, SKIP_NEW), saved[s])
    for s, ink in r84_ink.items():                          # ★ r83/r84 真字形
        CB.cell_write(plane_new, *cell(s, NCOL_NEW, SKIP_NEW), ink)
    for s in range(RES_LO, RES_HI + 1):
        CB.cell_write(plane_new, *cell(s, NCOL_NEW, SKIP_NEW), blank)
    for s, ink in borrow_ink.items():
        CB.cell_write(plane_new, *cell(s, NCOL_NEW, SKIP_NEW), ink)
    P('[pix ] 平面重建: 现役 %d 格重排 | 保留 %d 槽留空 | 借槽 %d 个 | 搬迁 %d 矩形 | '
      '条带清零 ✓' % (LIVE_HI + 1, RES_HI - RES_LO + 1, len(borrow_ink), len(move)))

    # ── ⑦ 断言 ──
    ink_new = raw_to_ink(bytes(plane_new), H)
    nb = sum(1 for s in range(LIVE_HI + 1)
             if not (CB.cell_read(bytes(plane_new), *cell(s, NCOL_NEW, SKIP_NEW))
                     == saved[s]).all())
    P('[A1] 现役 %d 格在新布局逐 texel == 基底: %s (不同 %d)'
      % (LIVE_HI + 1, '✓' if nb == 0 else '✗', nb))
    assert nb == 0
    nres = sum(1 for s in range(RES_LO, RES_HI + 1)
               if CB.cell_read(bytes(plane_new), *cell(s, NCOL_NEW, SKIP_NEW)).any())
    nr84 = [s for s, ink in r84_ink.items()
            if not (CB.cell_read(bytes(plane_new), *cell(s, NCOL_NEW, SKIP_NEW)) == ink).all()]
    nbw = [s for s, ink in borrow_ink.items()
           if not (CB.cell_read(bytes(plane_new), *cell(s, NCOL_NEW, SKIP_NEW)) == ink).all()]
    P('[A2] 保留槽 %d..%d 留空 %d/%d ✓ ; r83/r84 槽 %d..%d 逐 texel == 来源盘 %s ; '
      '借槽 %d 个逐 texel == 模板 %s (不符 %s)'
      % (RES_LO, RES_HI, (RES_HI - RES_LO + 1) - nres, RES_HI - RES_LO + 1,
         R84_LO, R84_HI, '✓' if not nr84 else '✗ %s' % nr84[:5],
         len(borrow_ink), '✓' if not nbw else '✗', nbw))
    assert nres == 0 and not nbw and not nr84

    bad3 = []
    for (fn, k, o, r6) in recs:
        r = (r6[2], r6[3], r6[4], r6[5])
        nr = move.get(r, r)
        old = ink_base[r[1]:r[3], r[0]:r[2]]
        new = ink_new[nr[1]:nr[3], nr[0]:nr[2]]
        if old.shape != new.shape or not (old == new).all():
            bad3.append((fn, k, (r, nr), int((old != new).sum())))
    P('[A3] ★ 全部 **%d** 条非空记录: 新窗像素 == 基底同记录窗像素 (逐 texel) %s ; '
      '其中被搬 %d 条 / 未搬 %d 条'
      % (len(recs), '✓' if not bad3 else '✗ %s' % bad3[:3],
         sum(len(distinct[r]) for r in move),
         len(recs) - sum(len(distinct[r]) for r in move)))
    assert not bad3

    used_ink2 = np.zeros((H, W), dtype=bool)
    for s in range(SLOT_LO, SLOT_HI + 1):
        x, y = cell(s, NCOL_NEW, SKIP_NEW)
        used_ink2[y:y + 16, x:x + 16] = CB.cell_read(bytes(plane_new), x, y)
    pol2 = []
    for (fn, k, o, r6) in recs:
        r = (r6[2], r6[3], r6[4], r6[5])
        nr = move.get(r, r)
        if used_ink2[nr[1]:nr[3], nr[0]:nr[2]].any():
            pol2.append((fn, k, r))
    P('[A4] ★ 记录窗含现役格墨的条数 = **%d** (搬迁前 %d 条) %s'
      % (len(pol2), sum(len(distinct[r]) for r in polluted), '✓' if not pol2 else '✗'))
    assert not pol2

    own = np.zeros((H, W), dtype=bool)
    for (fn, k, o, r6) in recs:
        r = (r6[2], r6[3], r6[4], r6[5])
        nr = move.get(r, r)
        own[nr[1]:nr[3], nr[0]:nr[2]] = True
    for s in range(SLOT_LO, SLOT_HI + 1):
        x, y = cell(s, NCOL_NEW, SKIP_NEW)
        own[y:y + 16, x:x + 16] = True
    orph = ink_new & ~own
    P('[A5] 无主墨 = **%d** texel %s' % (int(orph.sum()), '✓' if not orph.any() else '✗'))
    if orph.any():
        ys, xs = np.nonzero(orph)
        P('      样例 %s ; y %d..%d' % (list(zip(xs.tolist(), ys.tolist()))[:10], ys.min(),
                                        ys.max()))
    assert not orph.any()

    # ── ⑧ 容器回写 ──
    ct_new, segs_chk, covered = CB.plane_to_container(ct_stage, bytes(plane_new), W)
    assert len(ct_new) == len(ct_stage) and covered == payload
    assert [s[0] for s in segs_chk] == [s[0] for s in segs_new]
    assert [s[2] for s in segs_chk] == [s[2] for s in segs_new]
    ck_raw, _ = CB.container_to_plane(ct_new, W, H)
    assert ck_raw == bytes(plane_new)
    P('[ct  ] 新容器 %d B / %d 段 ; 段表逐项一致 ; 容器→引擎面 回环逐字节相同 ✓'
      % (len(ct_new), len(segs_chk)))
    pak_new = bytearray(pak_s)
    pak_new[PX_s:PX_s + px_s] = ct_new
    pak_new = bytes(pak_new)
    assert bytes(pak_new[:PX_s]) == bytes(pak_s[:PX_s])
    assert bytes(pak_new[PX_s + px_s:]) == bytes(pak_s[PX_s + px_s:])

    # ── ⑨ FONT.RES 记录改写 + 重压 ──
    ft = bytearray(ft_blob_b)
    off_of = {fn: rows[0][0] for (fn, fld, rows) in faces_b}
    uv_span, n_upd = [], 0
    for r, nw in move.items():
        for (fn, k, o, b0, b1) in distinct[r]:
            u0, v0, u1, v1 = struct.unpack_from('<4H', ft, o + 2)
            assert (u0, v0, u1, v1) == r, ('盘上矩形与分析不符', fn, k, (u0, v0, u1, v1), r)
            struct.pack_into('<BB4H', ft, o, b0, b1, nw[0], nw[1], nw[2], nw[3])
            uv_span.append((o + 2, o + 10))
            assert ft[o] == ft_blob_b[o] and ft[o + 1] == ft_blob_b[o + 1]
            n_upd += 1
    chg = [i for i in range(len(ft)) if ft[i] != ft_blob_b[i]]
    assert chg and all(any(lo <= i < hi for (lo, hi) in uv_span) for i in chg), '改动越界'
    P('[ft  ] FONT.RES: 改写 **%d 条记录**的 u0/v0/u1/v1 (%d 字节, 全在记录第 2..9 字节内); '
      'rec[0]/rec[1] 原值 ✓ ; 其它 %d 字节零改动 ✓'
      % (n_upd, len(chg), len(ft) - len(chg)))
    olen = subs_b[0][1]
    tail = ft_slot_b[8 + olen:]
    assert all(b == 0 for b in tail), 'FONT.RES 槽尾非零填充'
    new_frame = T.lzo_pack([(bytes(ft), len(ft))])
    assert len(new_frame) <= len(ft_slot_b), 'FONT.RES 重压超槽 %d > %d' % (len(new_frame),
                                                                            len(ft_slot_b))
    new_slot = new_frame + b'\x00' * (len(ft_slot_b) - len(new_frame))
    assert b''.join(s[0] for s in T.lzo_subs(new_slot)) == bytes(ft), 'FONT.RES 重压回环失败'
    P('[ft  ] FONT.RES 重压 %d → %d B (槽 %d, 余 %d B 补零) 回环逐字节一致 ✓'
      % (8 + olen, len(new_frame), len(ft_slot_b), len(ft_slot_b) - len(new_frame)))

    # ── ⑩ ELF 8 字节 ──
    elf_patch = []
    w0 = struct.unpack_from('<I', ist.mm, VA2ISO(ELF_COLS))[0]
    assert (w0 & 0xFFFF) == NCOL_OLD, hex(w0)
    elf_patch.append((ELF_COLS, VA2ISO(ELF_COLS), w0, (w0 & 0xFFFF0000) | NCOL_NEW,
                      'COLS %d→%d' % (NCOL_OLD, NCOL_NEW)))
    w0 = struct.unpack_from('<I', ist.mm, VA2ISO(ELF_SKIP))[0]
    assert w0 == 0x25AD0003, hex(w0)
    elf_patch.append((ELF_SKIP, VA2ISO(ELF_SKIP), w0, 0x25AD0002,
                      'SKIP_ROWS %d→%d' % (SKIP_OLD, SKIP_NEW)))
    # ★ Y0 2→3 + V1 18→19: 图集格整体下移 1 px ⇒ grid row12 由 y=226 变 **y=227**,
    #   跳过带里的 EN/ASCII 表 (195..226) 因此**一个矩形都不用搬**;
    #   SKIP 3→2 让出来的那第 38 行 (row37, y 627..642) 归 ASCII 表用。
    w0 = struct.unpack_from('<I', ist.mm, VA2ISO(ELF_Y0))[0]
    assert w0 == 0x25CD0002, hex(w0)
    elf_patch.append((ELF_Y0, VA2ISO(ELF_Y0), w0, 0x25CD0003, 'Y0 %d→%d' % (Y0_OLD, Y0_NEW)))
    w0 = struct.unpack_from('<I', ist.mm, VA2ISO(ELF_V1))[0]
    assert w0 == 0x25CE0012, hex(w0)
    elf_patch.append((ELF_V1, VA2ISO(ELF_V1), w0, 0x25CE0013,
                      'V1 = V0+16 : %d→%d' % (Y0_OLD + 16, Y0_NEW + 16)))
    for va in (() if a.keep_gate else ELF_GATE):
        off = VA2ISO(va)
        w0 = struct.unpack_from('<I', ist.mm, off)[0]
        assert (w0 >> 26) == 0x0B and (w0 & 0xFFFF) == GATE_OLD, (hex(va), hex(w0))
        elf_patch.append((va, off, w0, (w0 & 0xFFFF0000) | GATE_NEW,
                          'GATE 0x%02X→0x%02X' % (GATE_OLD, GATE_NEW)))
    if a.keep_gate:
        P('[elf ] ★ --keep-gate 单变量对照: GATE 4 站点保持 0x%02X (只动 COLS/SKIP/Y0/V1)'
          % GATE_OLD)
    for (va, off, w0, w1, tg) in elf_patch:
        P('[elf ] VA 0x%08X ISO 0x%08X  %08X → %08X  (%s)' % (va, off, w0, w1, tg))
    nbytes = sum(1 for (va, off, w0, w1, tg) in elf_patch if (w0 ^ w1) & 0xFFFF)
    P('[elf ] ELF 改动 = **%d 个字节** (COLS/SKIP/Y0/V1%s)'
      % (nbytes, '' if a.keep_gate else ' + GATE×4'))
    assert nbytes == (4 if a.keep_gate else 8), nbytes

    if a.dry_run:
        P('[dry ] 未写盘')
        _save(a.tag, dict(dry=True, n_reloc_rects=len(move), n_reloc_recs=n_upd), a)
        return 0

    # ── ⑪ 写盘 + 回读 ──
    for (dst, mode) in ((a.out, 'geom'), (a.allpat_out, 'allpat')):
        with open(a.stage, 'rb') as fi, open(dst, 'wb') as fo:
            shutil.copyfileobj(fi, fo, 1 << 22)
        ct_w = ct_new
        if mode == 'allpat':
            pb = bytearray(plane_new)
            for s in range(SLOT_LO, SLOT_HI + 1):
                CB.cell_write(pb, *cell(s, NCOL_NEW, SKIP_NEW), CB.slot_pattern(s))
            ct_w, sg, cv = CB.plane_to_container(ct_stage, bytes(pb), W)
            assert len(ct_w) == len(ct_stage) and cv == payload
            P('[allpat] 全部 %d 槽写可解码图案 (离线寻址证明盘, 不跑模拟器)' % (SLOT_HI + 1))
        with open(dst, 'r+b') as f:
            f.seek(MENU_BASE + e_pak_s['off'] + PX_s)
            f.write(ct_w)
            f.seek(e_ft_s['iso_off'])
            f.write(new_slot)
            for (va, off, w0, w1, tg) in elf_patch:
                f.seek(off)
                f.write(struct.pack('<I', w1))
        sha = CB.sha256_file(dst)
        P('[out ] %s  %d B (%d sect)  sha256=%s'
          % (dst, os.path.getsize(dst), os.path.getsize(dst) // 2048, sha))
        iz = T.Iso(dst)
        ez = zx_lib.entries(iz, zx_lib.MENU_LBA)
        e_pz = [e for e in ez if e['name'] == 'COMMON.PAK'][0]
        e_fz = [e for e in ez if e['name'] == 'FONT.RES'][0]
        assert (e_pz['off'], e_pz['stored'], e_pz['real']) == \
            (e_pak_s['off'], e_pak_s['stored'], e_pak_s['real'])
        assert zx_lib.header(iz, zx_lib.MENU_LBA)['size'] == hdr_s['size']
        assert zx_lib.names_region(iz, zx_lib.MENU_LBA) == names_s
        assert zx_lib.hash_region(iz, zx_lib.MENU_LBA) == hash_s
        pak_z = bytes(iz.read(e_pz['iso_off'], e_pz['stored']))
        rz = T.parse_pak_records(pak_z)
        ctz = bytes(pak_z[rz[1][6]:rz[1][6] + rz[1][5]])
        plz_raw, segz = CB.container_to_plane(ctz, W, H)
        assert ctz == ct_w
        ftz = bytes(iz.read(e_fz['iso_off'], e_fz['stored']))
        assert ftz == new_slot
        fz, _ = zx_lib.ft_records(b''.join(s[0] for s in T.lzo_subs(ftz)), 28)
        for (va, off, w0, w1, tg) in elf_patch:
            assert struct.unpack_from('<I', iz.mm, off)[0] == w1, hex(va)
        plz = raw_to_ink(plz_raw, H)
        P('[R1 ] 回读 容器 %d B / %d 段 / %dx%d px_size=0x%X ; 逐字节 == 写前 ✓'
          % (len(ctz), len(segz), rz[1][2], rz[1][3], rz[1][5]))
        P('[R2 ] 回读 ELF: COLS=%d ; SKIP=%d ; GATE 4/4 = 0x%02X ✓'
          % (struct.unpack_from('<I', iz.mm, VA2ISO(ELF_COLS))[0] & 0xFFFF,
             struct.unpack_from('<I', iz.mm, VA2ISO(ELF_SKIP))[0] & 0xFFFF, GATE_NEW))
        P('[R3 ] 回读 FONT.RES 槽 %d B 逐字节 == 写前 ✓ ; 记录表回环 ✓' % len(ftz))
        if mode == 'geom':
            ok_live = sum(1 for s in range(LIVE_HI + 1)
                          if (CB.cell_read(plz_raw, *cell(s, NCOL_NEW, SKIP_NEW))
                              == saved[s]).all())
            ok_bor = sum(1 for s, ink in borrow_ink.items()
                         if (CB.cell_read(plz_raw, *cell(s, NCOL_NEW, SKIP_NEW))
                             == ink).all())
            ok_res = sum(1 for s in range(RES_LO, RES_HI + 1)
                         if not CB.cell_read(plz_raw, *cell(s, NCOL_NEW, SKIP_NEW)).any())
            ok_r84 = sum(1 for s, ink in r84_ink.items()
                         if (CB.cell_read(plz_raw, *cell(s, NCOL_NEW, SKIP_NEW)) == ink).all())
            ok_rec = 0
            for (fn, k, o, r6) in recs:
                nr = move.get((r6[2], r6[3], r6[4], r6[5]), (r6[2], r6[3], r6[4], r6[5]))
                if (plz[nr[1]:nr[3], nr[0]:nr[2]]
                        == ink_base[r6[3]:r6[5], r6[2]:r6[4]]).all():
                    ok_rec += 1
            P('[R4 ] 回读 现役 %d/%d ✓ ; r83/r84 %d/%d ✓ ; 借槽 %d/%d ✓ ; 保留槽空 %d/%d ✓ ; '
              '★ 记录窗 == 基底 **%d/%d** %s'
              % (ok_live, LIVE_HI + 1, ok_r84, len(r84_ink), ok_bor, len(borrow_ink), ok_res,
                 RES_HI - RES_LO + 1, ok_rec, len(recs),
                 '✓' if (ok_live == LIVE_HI + 1 and ok_r84 == len(r84_ink)
                         and ok_bor == len(borrow_ink)
                         and ok_res == RES_HI - RES_LO + 1 and ok_rec == len(recs)) else '✗'))
            assert (ok_live == LIVE_HI + 1 and ok_r84 == len(r84_ink)
                    and ok_bor == len(borrow_ink)
                    and ok_res == RES_HI - RES_LO + 1 and ok_rec == len(recs))
            n_in, n_out, ex = CB.compare_windows(
                dst, a.base, hdr_s['size'],
                extra=[(off, off + 4) for (_va, off, _o, _n, _t) in elf_patch])
            P('[D  ] 全盘差异 (vs 基底 GR_ZH124): 计划窗口内 %d B ; **窗口外 %d B** %s'
              % (n_in, n_out, '✓' if n_out == 0 else '✗ %s' % ex))
            assert n_out == 0, ex
        else:
            ok_all = 0
            for s in range(SLOT_LO, SLOT_HI + 1):
                okl, got, _why = CB.pattern_decode(
                    CB.cell_read(plz_raw, *cell(s, NCOL_NEW, SKIP_NEW)))
                ok_all += 1 if (okl and got == s) else 0
            P('[R4-allpat] 回读 **全部 %d 槽** 图案解码 == 槽号: %d ✓' % (SLOT_HI + 1, ok_all))
            assert ok_all == SLOT_HI + 1
        iz.close()
    _save(a.tag, dict(dry=False, h=H, w=W, ncol=NCOL_NEW, skip_rows=SKIP_NEW, gate=GATE_NEW,
                      slots=[SLOT_LO, SLOT_HI], live=[0, LIVE_HI],
                      reserved=[RES_LO, RES_HI], n_reserved=RES_HI - RES_LO + 1,
                      borrow=sorted(borrow_ink), xmark_ink=int(xg.sum()),
                      nrow=nrow, cells=nrow * NCOL_NEW,
                      n_records=len(recs), n_reloc_rects=len(move), n_reloc_recs=n_upd,
                      reloc={str(k): list(v) for k, v in move.items()},
                      ft_frame=[8 + olen, len(new_frame)], ft_slot=len(ft_slot_b),
                      elf_patch=[dict(va='0x%08X' % va, iso='0x%08X' % off, old='%08X' % w0,
                                      new='%08X' % w1, tag=tg)
                                 for (va, off, w0, w1, tg) in elf_patch],
                      sha256={os.path.basename(p): CB.sha256_file(p)
                              for p in (a.stage, a.out, a.allpat_out)}), a)
    ib.close()
    ist.close()
    return 0


def _save(tag, extra, a):
    d = dict(extra=extra, log=LOG)
    with io.open(os.path.join(OUTDIR, 'cap_build_%s_report.json' % tag), 'w',
                 encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'cap_build_%s.log' % tag), 'w',
                 encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % os.path.join(OUTDIR, 'cap_build_%s_report.json' % tag))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
