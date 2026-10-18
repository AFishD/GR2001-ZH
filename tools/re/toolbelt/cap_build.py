# -*- coding: utf-8 -*-
r"""cap_build.py -- Step 2: 造探针盘 (h / 列数 / GATE 0xBA / 槽 0..2349 全部可寻址)

    # ① 任务书指定的几何: h=644 / 64 列
    python tools/re/toolbelt/cap_build.py --base work/builds/GR_ZH124/GR_ZH124.iso \
        --stage work/builds/GR_CAP2400/_stage644.iso \
        --out   work/builds/GR_CAP2400/GR_CAP2400.iso \
        --allpat-out work/builds/GR_CAP2400/GR_CAP2400_allpat.iso \
        --h 644 --ncol 64
    # ② 规避「ASCII 条带」的替代几何: h=660 / 62 列 (62 列 = 不动列数, 只抬 h + GATE)
    python tools/re/toolbelt/cap_build.py ... --h 660 --ncol 62

两段式 (与 REPORT_final_364.md §4 同一配方):
  ① `thr_patch_atlas.py --w 1024 --h <h> --real-mode fixed` ⇒ 只改图集几何 (h + 容器 + 条目表)
  ② 本脚本 ⇒ 图集重排 (62→ncol 列) + 探针图案 + ELF (COLS 62→ncol, GATE 0xB4→0xBA ×4)

不变式 (硬断言, 违反即中止):
  ① real 不变式 : COMMON.PAK 条目 stored(+0x18) == real(+0x1C)      [由 thr_patch_atlas 保证]
  ② px_size 不变式: px_size == w*h/2 + 16 且 payload == w*h/2 - nseg*48
  ③ 现役字形不动: 槽 0..1735 的 16x16 **逐 texel** == 基底盘同槽 (ncol=64 时从 62 列格搬到 64 列格)
  ④ 新槽可寻址: 槽 1736..2349 每格 == 该槽的确定性格子图案 (12 bit 槽号 + 边框 + 双同步字)
  ⑤ 记录带不动: 不与任何网格格位相交的 FT 记录矩形逐 texel 不变; 相交的逐条登记并量化
"""
import argparse
import hashlib
import io
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH124', 'GR_ZH124.iso')
THR = os.path.join(HERE, 'thr_patch_atlas.py')

W, H_OLD = 1024, 512
NCOL_OLD = 62
SLOT_LO, SLOT_HI = 0, 2349
LIVE_HI = 1735
GATE_OLD, GATE_NEW = 0xB4, 0xBA
ELF_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
COLS_VA = 0x4170AC
VA2ISO = lambda va: va - 0x6C780
MENU_BASE = zx_lib.MENU_LBA * 2048
EMPTY_NIB = 0x1
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ═══════════════════ 引擎格几何 (cave 反汇编同一张配方单) ═══════════════════

def yrow(row):
    return 2 + 16 * (row + (3 if row >= 12 else 0))


def cell(slot, ncol):
    return 16 * (slot % ncol), yrow(slot // ncol)


def rows_fit(h):
    r = 0
    while yrow(r) + 16 <= h:
        r += 1
    return r


def cells_of(h, ncol, n=SLOT_HI + 1):
    return {cell(s, ncol): s for s in range(n)}


# ═══════════════════ 确定性格子图案 ═══════════════════

def slot_pattern(slot):
    g = np.zeros((16, 16), dtype=bool)
    g[0, :] = True
    g[13, :] = True
    g[14, 2:15:2] = True
    g[15, 1:14:2] = True
    g[:, 0] = True
    g[:, 15] = True
    for k in range(12):
        if (slot >> k) & 1:
            g[1 + k, 2:14] = True
    return g


def pattern_decode(g):
    if not g[0, :].all() or not g[13, :].all():
        return False, -1, '上下边框不是全墨'
    if not g[:, 0].all() or not g[:, 15].all():
        return False, -1, '左右边框不是全墨'
    if list(g[14, 2:15:2]) != [True] * 7 or any(g[14, x] for x in (1, 3, 5, 7, 9, 11, 13)):
        return False, -1, '同步字 A (row14) 不符'
    if list(g[15, 1:14:2]) != [True] * 7 or any(g[15, x] for x in (2, 4, 6, 8, 10, 12, 14)):
        return False, -1, '同步字 B (row15) 不符'
    slot = 0
    for k in range(12):
        seg = g[1 + k, 2:14]
        if seg.all():
            slot |= (1 << k)
        elif seg.any():
            return False, -1, 'row%d 数据位既非全墨也非全空' % (1 + k)
    if not (SLOT_LO <= slot <= SLOT_HI):
        return False, slot, '槽号 %d 超出探针区间' % slot
    return True, slot, ''


# ═══════════════════ 引擎口径像素面 ═══════════════════

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


def plane_to_container(stage_cont, plane, w):
    stride = w // 2
    out = bytearray(stage_cont)
    segs = [s for s in T.atlas_container_segments(bytes(stage_cont), stride) if s[2] > 0]
    covered = 0
    for (row0, doff, nb) in segs:
        nfull, rest = nb // stride, nb % stride
        for i in range(nfull):
            out[doff + i * stride:doff + (i + 1) * stride] = \
                plane[(row0 + i) * stride:(row0 + i + 1) * stride]
        if rest:
            d = (row0 + nfull) * stride
            out[doff + nfull * stride:doff + nfull * stride + rest] = plane[d:d + rest]
        covered += nb
    return bytes(out), segs, covered


def cell_read(plane, x, y, w=W):
    stride = w // 2
    assert x % 16 == 0
    o = x // 2
    g = np.zeros((16, 16), dtype=bool)
    for i in range(16):
        r = plane[(y + i) * stride + o:(y + i) * stride + o + 8]
        assert len(r) == 8, (x, y, i, len(r))
        g[i, 0::2] = [(b & 0x0F) == 0 for b in r]
        g[i, 1::2] = [(b >> 4) == 0 for b in r]
    return g


def cell_write(plane, x, y, g, w=W):
    stride = w // 2
    assert x % 16 == 0 and g.shape == (16, 16)
    o = x // 2
    for i in range(16):
        row = bytearray(8)
        for k in range(8):
            lo = EMPTY_NIB if not g[i, 2 * k] else 0
            hi = EMPTY_NIB if not g[i, 2 * k + 1] else 0
            row[k] = (hi << 4) | lo
        plane[(y + i) * stride + o:(y + i) * stride + o + 8] = row


def rect_bytes(plane, r, w=W):
    """矩形覆盖的 texel 字节 (按行切片, nibble 级精确)。

    r 可以是 6 元组 `<BB4H>` (FT 原始记录) 或 4 元组 (u0,v0,u1,v1)。
    """
    u0, v0, u1, v1 = (r[2], r[3], r[4], r[5]) if len(r) == 6 else (r[0], r[1], r[2], r[3])
    stride = w // 2
    out = bytearray()
    for y in range(v0, v1):
        out += plane[y * stride + u0 // 2:y * stride + (u1 + 1) // 2]
    return bytes(out)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


# ═══════════════════ 主流程 ═══════════════════

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--stage', default=None)
    ap.add_argument('--out', default=None)
    ap.add_argument('--allpat-out', default=None)
    ap.add_argument('--h', type=int, default=644)
    ap.add_argument('--ncol', type=int, default=64)
    ap.add_argument('--rebuild-stage', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-pattern', action='store_true',
                    help='不写探针图案 (只搬现役字形 + 改 ELF) —— 供「几何体检」取证: '
                         '探针图案的墨紧贴现役格, 会被 glyph_geometry 判成"窗外无主墨"')
    ap.add_argument('--keep-gate', action='store_true',
                    help='**不改** GATE (保持基底 0xB4) —— 单变量探针: 只动 h / 列数, '
                         '文本行为与基底完全一致, 便于把"ASCII 条带被覆盖"从"抬闸门吞字节"里分离出来')
    ap.add_argument('--tag', default=None)
    a = ap.parse_args(argv)
    tag = a.tag or ('h%d_c%d' % (a.h, a.ncol))
    a.stage = a.stage or os.path.join(OUTDIR, '_stage%d.iso' % a.h)
    a.out = a.out or os.path.join(OUTDIR, 'GR_CAP2400.iso')
    a.allpat_out = a.allpat_out or os.path.join(OUTDIR, 'GR_CAP2400_allpat.iso')
    os.makedirs(OUTDIR, exist_ok=True)
    P('=' * 96)
    P('cap_build.py  探针盘 %s : h=%d / %d 列 / GATE 0x%02X / 槽 %d..%d'
      % (tag, a.h, a.ncol, GATE_NEW, SLOT_LO, SLOT_HI))
    P('  base  = %s' % a.base)
    P('  stage = %s' % a.stage)
    P('  out   = %s' % a.out)
    P('=' * 96)

    # ⓪ 第一段: 只加高图集
    if a.rebuild_stage or not os.path.exists(a.stage):
        cmd = [sys.executable, THR, a.base, a.stage, '--w', str(W), '--h', str(a.h),
               '--real-mode', 'fixed',
               '--report', os.path.join(OUTDIR, 'stage%d_report.json' % a.h)]
        P('[stage] %s' % ' '.join(cmd))
        r = subprocess.run(cmd, cwd=REPO)
        assert r.returncode == 0, 'thr_patch_atlas.py 失败 rc=%d' % r.returncode
    else:
        P('[stage] 复用已存在的 %s (sha256=%s)' % (a.stage, sha256_file(a.stage)))
    base_sz, stage_sz = os.path.getsize(a.base), os.path.getsize(a.stage)
    P('[iso ] base %d B (%d sect) ; stage %d B (%d sect) ; Δ=%+d B'
      % (base_sz, base_sz // 2048, stage_sz, stage_sz // 2048, stage_sz - base_sz))

    # ① 基底盘
    ib = T.Iso(a.base)
    eb = zx_lib.entries(ib, zx_lib.MENU_LBA)
    e_pak_b = [e for e in eb if e['name'] == 'COMMON.PAK'][0]
    e_ft_b = [e for e in eb if e['name'] == 'FONT.RES'][0]
    pak_b = bytes(ib.read(e_pak_b['iso_off'], e_pak_b['stored']))
    rb = T.parse_pak_records(pak_b)
    assert rb[1][0] == 'new_font_revised' and (rb[1][2], rb[1][3]) == (W, H_OLD)
    assert rb[1][5] == W * H_OLD // 2 + 16
    plane_old, segs_old = container_to_plane(bytes(pak_b[rb[1][6]:rb[1][6] + rb[1][5]]), W, H_OLD)
    ft_slot = bytes(ib.read(e_ft_b['iso_off'], e_ft_b['stored']))
    ft_blob = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, ft_end = zx_lib.ft_records(ft_blob, 28)
    nrecs = [(f[0], f[1][4] * f[1][5]) for f in faces]
    recs_ne = [(fn, k, r) for (fn, _fl, rows) in faces for k, (o, r) in enumerate(rows)
               if r[4] > r[2] and r[5] > r[3]]
    P('[base] PAK %d B ; rec#1 %dx%d px_size=0x%X ; 容器 %d B / %d 段'
      % (len(pak_b), rb[1][2], rb[1][3], rb[1][5], rb[1][5], len(segs_old)))
    P('[base] FONT.RES 槽 %d B / 展开 %d B ; nrec %s ; 非空记录 **%d**'
      % (len(ft_slot), len(ft_blob), nrecs, len(recs_ne)))
    live = {}
    for s in range(LIVE_HI + 1):
        g = cell_read(plane_old, *cell(s, NCOL_OLD))
        assert g.any(), '基底盘槽 %d 无墨' % s
        live[s] = g
    P('[base] 现役槽 **%d** 个 (%d..%d), 每格都有墨 ✓' % (len(live), min(live), max(live)))

    # ①b ★ 右边缘 ASCII 条带 (x>=992 = 第 62/63 列) —— 64 列方案的真实代价
    strip = {}
    for (fn, k, r) in recs_ne:
        if r[2] >= 992:
            strip.setdefault(r, []).append((fn, k))
    strip_texels = sum((r[4] - r[2]) * (r[5] - r[3]) for r in strip)
    codes = sorted(set(k + 0x20 for v in strip.values() for (_f, k) in v))
    P('[strip] ★ 右边缘 x>=992 的 ASCII 条带: **%d** 个不同矩形, 被 %d 条记录引用, %d texel'
      % (len(strip), sum(len(v) for v in strip.values()), strip_texels))
    P('[strip]    覆盖码位 0x%02X..0x%02X (%d 个), 三个 face 共享同一批矩形'
      % (min(codes), max(codes), len(codes)))

    # ② stage 盘
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
    assert (nm_s, psm_s, w_s, h_s, clut_s) == ('new_font_revised', 0x14, W, a.h, 1040)
    assert px_s == W * a.h // 2 + 16, px_s
    assert (W * a.h // 2) % 2048 == 0
    ct_stage = bytes(pak_s[PX_s:PX_s + px_s])
    plane_stage, segs_new = container_to_plane(ct_stage, W, a.h)
    payload = sum(s[2] for s in segs_new)
    assert payload == W * a.h // 2 - len(segs_new) * 48, (payload, len(segs_new))
    P('[stage] PAK %d B ; rec#1 %dx%d px_size=0x%X (=w*h/2+16 ✓) ; 容器 %d B / **%d 段** / payload %d'
      % (len(pak_s), w_s, h_s, px_s, len(ct_stage), len(segs_new), payload))
    P('[stage] 不变式②: payload == w*h/2 - %d*48 ✓ ; (w*h/2)%%2048 = 0 ✓ ; stored==real==%d ✓'
      % (len(segs_new), e_pak_s['stored']))
    assert plane_stage[:W // 2 * H_OLD] == plane_old, 'stage 的旧像素与基底不一致'
    P('[stage] 旧 512 行像素逐行 == 基底 ✓')

    nrow = rows_fit(a.h)
    P('[geom] h=%d ⇒ 网格行 0..%d (%d 行) × %d 列 = **%d 格** ; 目标 %d 槽 ⇒ 余 %d 格'
      % (a.h, nrow - 1, nrow, a.ncol, nrow * a.ncol, SLOT_HI + 1, nrow * a.ncol - SLOT_HI - 1))
    assert SLOT_HI + 1 <= nrow * a.ncol, (nrow * a.ncol, SLOT_HI + 1)
    P('[geom] 容量表 (同一 h 下 62 vs 64 列):')
    for hh in (512, 640, 644, 648, 652, 656, 660, 664, 668, 672):
        note = []
        if hh == a.h:
            note.append('← 本轮')
        if rows_fit(hh) * 64 >= SLOT_HI + 1:
            note.append('64 列可达 %d' % (SLOT_HI + 1))
        if rows_fit(hh) * 62 >= SLOT_HI + 1:
            note.append('62 列可达 %d' % (SLOT_HI + 1))
        P('        h=%-4d 行数 %-3d  62 列 %-5d  64 列 %-5d  px_size %-7d %s'
          % (hh, rows_fit(hh), rows_fit(hh) * 62, rows_fit(hh) * 64, W * hh // 2 + 16,
             ' '.join(note)))
    cells = {}
    for s in range(SLOT_LO, SLOT_HI + 1):
        x, y = cell(s, a.ncol)
        assert 0 <= x and x + 16 <= W and 0 <= y and y + 16 <= a.h, (s, x, y)
        assert (x, y) not in cells, '格位重复: 槽 %d 与 %d' % (s, cells[(x, y)])
        cells[(x, y)] = s
    P('[geom] 槽 %d..%d 全部映射到**互不重复**且在图集内的 16x16 格 ✓ (%d 格)'
      % (SLOT_LO, SLOT_HI, len(cells)))

    # ③ 新像素面
    plane_new = bytearray(plane_stage)
    if a.ncol != NCOL_OLD:
        blank = np.zeros((16, 16), dtype=bool)
        for s in range(LIVE_HI + 1):
            cell_write(plane_new, *cell(s, NCOL_OLD), blank)
        P('[pix ] 重排第 1 步: 把老布局的 %d 个格清成空 (0x11) —— 新布局里这些格属于别的槽'
          % (LIVE_HI + 1))
    moved = 0
    for s in range(LIVE_HI + 1):
        xs, ys = cell(s, NCOL_OLD)
        xd, yd = cell(s, a.ncol)
        if (xs, ys) != (xd, yd):
            moved += 1
        cell_write(plane_new, xd, yd, live[s])
    if a.ncol == NCOL_OLD:
        P('[pix ] 列数未变 ⇒ 现役字形**原位不动** (0 个位置变化), 逐 texel 原样')
    else:
        P('[pix ] 重排第 2 步: 现役字形落到 64 列格位, %d / %d 个位置变了; 全部逐 texel 原样'
          % (moved, LIVE_HI + 1))
    for s in range(LIVE_HI + 1, SLOT_HI + 1):
        if a.no_pattern:
            break
        cell_write(plane_new, *cell(s, a.ncol), slot_pattern(s))
    if a.no_pattern:
        P('[pix ] ★ --no-pattern: 槽 %d..%d 保持空白 (不写图案) —— 只用于几何体检取证'
          % (LIVE_HI + 1, SLOT_HI))
    else:
        P('[pix ] 探针图案: 槽 %d..%d (**%d** 个)' % (LIVE_HI + 1, SLOT_HI, SLOT_HI - LIVE_HI))

    # ④ 断言
    nbad = sum(1 for s in range(LIVE_HI + 1)
               if not (cell_read(bytes(plane_new), *cell(s, a.ncol)) == live[s]).all())
    P('[A1] 现役槽 %d 个在新布局格里逐 texel == 基底盘同槽: %s (不同 %d)'
      % (LIVE_HI + 1, '✓' if nbad == 0 else '✗', nbad))
    assert nbad == 0
    if not a.no_pattern:
        nb2 = 0
        for s in range(LIVE_HI + 1, SLOT_HI + 1):
            ok, got, why = pattern_decode(cell_read(bytes(plane_new), *cell(s, a.ncol)))
            nb2 += 0 if (ok and got == s) else 1
        P('[A2] 槽 %d..%d 图案解码回槽号: %s (失败 %d)'
          % (LIVE_HI + 1, SLOT_HI, '✓' if nb2 == 0 else '✗', nb2))
        assert nb2 == 0
    else:
        nblank = sum(1 for s in range(LIVE_HI + 1, SLOT_HI + 1)
                     if not cell_read(bytes(plane_new), *cell(s, a.ncol)).any())
        P('[A2] --no-pattern: 槽 %d..%d 全空白 %d/%d ✓'
          % (LIVE_HI + 1, SLOT_HI, nblank, SLOT_HI - LIVE_HI))
        assert nblank == SLOT_HI - LIVE_HI

    # ④b 记录带: 与网格**格位**相交的才可能变; 不相交的必须逐 texel 不变
    old_rects = [(x, y, x + 16, y + 16) for (x, y) in cells_of(H_OLD, NCOL_OLD, LIVE_HI + 1)]
    new_rects = [(x, y, x + 16, y + 16) for (x, y) in cells]

    def hits(r, rects):
        return any(r[2] < b and a < r[4] and r[3] < d and c < r[5] for (a, c, b, d) in rects)

    safe, over = [], []
    for (fn, k, r) in recs_ne:
        (over if (hits(r, old_rects) or hits(r, new_rects)) else safe).append((fn, k, r))
    chg = [t for t in safe
           if rect_bytes(plane_old, t[2]) != rect_bytes(bytes(plane_new), t[2])]
    P('[A3] FT 记录 %d 条非空: 与任一网格格位**不相交**的 %d 条 → 逐 texel 不变 %s'
      % (len(recs_ne), len(safe), '✓' if not chg else '✗ 变了 %d 条' % len(chg)))
    assert not chg, chg[:5]
    P('[A3] 与网格格位相交的 %d 条: 其中落在**右边缘 ASCII 条带** (x>=992) 的 %d 条'
      % (len(over), sum(1 for (_f, _k, r) in over if r[2] >= 992)))
    strip_kept = sum(1 for r in strip if rect_bytes(plane_old, r) == rect_bytes(bytes(plane_new), r))
    P('[A3] ★ ASCII 条带: %d 个矩形中 **%d 个逐 texel 不变**, %d 个被网格格位覆盖 (ncol=%d)'
      % (len(strip), strip_kept, len(strip) - strip_kept, a.ncol))
    band_ok = all(plane_stage[y * (W // 2):(y + 1) * (W // 2)]
                  == bytes(plane_new)[y * (W // 2):(y + 1) * (W // 2)] for y in range(194, 242))
    P('[A4] 3 行跳过带 (y 194..241) 逐字节不变: %s' % ('✓' if band_ok else '✗'))
    assert band_ok
    cov = np.zeros((a.h, W), dtype=bool)
    for (x, y) in cells:
        cov[y:y + 16, x:x + 16] = True
    tail = bytes(plane_new)[H_OLD * (W // 2):]
    tail_stage = plane_stage[H_OLD * (W // 2):]
    outside = 0
    stride = W // 2
    for y in range(H_OLD, a.h):
        for xb in range(stride):
            if tail[(y - H_OLD) * stride + xb] != tail_stage[(y - H_OLD) * stride + xb]:
                x0 = xb * 2
                if not (cov[y, x0] or cov[y, x0 + 1]):
                    outside += 1
    P('[A5] 新区域 (y>=%d, %d B) 的改动**全部落在新格内**: 格外的改动字节 = %d %s'
      % (H_OLD, len(tail), outside, '✓' if outside == 0 else '✗'))
    assert outside == 0

    # ⑤ 容器回写 + ELF
    ct_new, segs_chk, covered = plane_to_container(ct_stage, bytes(plane_new), W)
    assert len(ct_new) == len(ct_stage) and covered == payload
    assert [s[0] for s in segs_chk] == [s[0] for s in segs_new]
    assert [s[2] for s in segs_chk] == [s[2] for s in segs_new]
    ck_plane, _ = container_to_plane(ct_new, W, a.h)
    assert ck_plane == bytes(plane_new)
    P('[ct  ] 新容器 %d B ; 段表逐项一致 ; 容器→引擎面 回环逐字节相同 ✓' % len(ct_new))
    pak_new = bytearray(pak_s)
    pak_new[PX_s:PX_s + px_s] = ct_new
    pak_new = bytes(pak_new)
    assert len(pak_new) == len(pak_s)
    r2 = T.parse_pak_records(pak_new)
    assert (r2[1][2], r2[1][3], r2[1][5]) == (W, a.h, px_s)
    assert bytes(pak_new[:PX_s]) == bytes(pak_s[:PX_s])
    assert bytes(pak_new[PX_s + px_s:]) == bytes(pak_s[PX_s + px_s:])
    P('[pak ] 新 PAK %d B (同长) ; rec#1 %dx%d px_size=0x%X ✓ ; 容器外字节不变 ✓'
      % (len(pak_new), r2[1][2], r2[1][3], r2[1][5]))

    elf_patch = []
    if a.ncol != NCOL_OLD:
        w0 = struct.unpack_from('<I', ist.mm, VA2ISO(COLS_VA))[0]
        assert (w0 & 0xFFFF) == NCOL_OLD, hex(w0)
        w1 = (w0 & 0xFFFF0000) | a.ncol
        elf_patch.append((COLS_VA, VA2ISO(COLS_VA), w0, w1,
                          'COLS %d→%d' % (NCOL_OLD, a.ncol)))
    for va in (() if a.keep_gate else ELF_SITES):
        off = VA2ISO(va)
        w0 = struct.unpack_from('<I', ist.mm, off)[0]
        assert (w0 >> 26) == 0x0B and (w0 & 0xFFFF) == GATE_OLD, (hex(va), hex(w0))
        elf_patch.append((va, off, w0, (w0 & 0xFFFF0000) | GATE_NEW,
                          'GATE 0x%02X→0x%02X' % (GATE_OLD, GATE_NEW)))
    if a.keep_gate:
        P('[elf ] --keep-gate: GATE 4 站点保持 0x%02X (单变量: 只动 h/列数)' % GATE_OLD)
    for (va, off, w0, w1, tg) in elf_patch:
        P('[elf ] VA 0x%08X ISO 0x%08X  %08X → %08X  (%s)' % (va, off, w0, w1, tg))
    P('[elf ] ELF 改动 = **%d 字节** (每字只改小端 imm 低字节)' % len(elf_patch))

    if a.dry_run:
        P('[dry ] 未写盘')
        _save(tag, dict(dry=True))
        return 0

    # ⑥ 写盘 (probe [+ allpat])
    todo = [(a.out, 'probe')] if a.no_pattern else [(a.out, 'probe'), (a.allpat_out, 'allpat')]
    for (dst, mode) in todo:
        os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
        ct_w = ct_new
        if mode == 'allpat':
            pl = bytearray(plane_stage)
            for s in range(SLOT_LO, SLOT_HI + 1):
                cell_write(pl, *cell(s, a.ncol), slot_pattern(s))
            ct_w, sg, cv = plane_to_container(ct_stage, bytes(pl), W)
            assert len(ct_w) == len(ct_stage) and cv == payload
            P('[allpat] 全部 %d 个槽写图案 (离线可寻址证明盘, 不跑模拟器)' % (SLOT_HI + 1))
        with open(a.stage, 'rb') as fi, open(dst, 'wb') as fo:
            while True:
                blk = fi.read(1 << 22)
                if not blk:
                    break
                fo.write(blk)
        with open(dst, 'r+b') as f:
            f.seek(MENU_BASE + e_pak_s['off'] + PX_s)
            f.write(ct_w)
            for (va, off, w0, w1, tg) in elf_patch:
                f.seek(off)
                f.write(struct.pack('<I', w1))
        sha = sha256_file(dst)
        P('[out ] %s  %d B (%d sect)  sha256=%s'
          % (dst, os.path.getsize(dst), os.path.getsize(dst) // 2048, sha))
        iz = T.Iso(dst)
        ez = zx_lib.entries(iz, zx_lib.MENU_LBA)
        e_pz = [e for e in ez if e['name'] == 'COMMON.PAK'][0]
        e_fz = [e for e in ez if e['name'] == 'FONT.RES'][0]
        assert (e_pz['off'], e_pz['stored'], e_pz['real']) == \
            (e_pak_s['off'], e_pak_s['stored'], e_pak_s['real'])
        assert e_pz['stored'] == e_pz['real']
        assert zx_lib.header(iz, zx_lib.MENU_LBA)['size'] == hdr_s['size']
        assert zx_lib.names_region(iz, zx_lib.MENU_LBA) == names_s
        assert zx_lib.hash_region(iz, zx_lib.MENU_LBA) == hash_s
        pak_z = bytes(iz.read(e_pz['iso_off'], e_pz['stored']))
        rz = T.parse_pak_records(pak_z)
        ctz = bytes(pak_z[rz[1][6]:rz[1][6] + rz[1][5]])
        plz, segz = container_to_plane(ctz, W, a.h)
        assert ctz == ct_w
        for (va, off, w0, w1, tg) in elf_patch:
            assert struct.unpack_from('<I', iz.mm, off)[0] == w1, hex(va)
        assert bytes(iz.read(e_fz['iso_off'], e_fz['stored'])) == ft_slot
        assert e_fz['off'] == e_ft_s['off']
        P('[R1 ] 回读 容器 %d B / %d 段 / %dx%d px_size=0x%X ; 逐字节 == 写前 ✓'
          % (len(ctz), len(segz), rz[1][2], rz[1][3], rz[1][5]))
        P('[R2 ] 回读 ELF: COLS=%d (期望 %d) ; GATE 4/4 = 0x%02X ✓'
          % (struct.unpack_from('<I', iz.mm, VA2ISO(COLS_VA))[0] & 0xFFFF, a.ncol, GATE_NEW))
        P('[R3 ] 回读 FONT.RES %d B 逐字节 == 基底 ✓ ; nrec %s' % (len(ft_slot), nrecs))
        ok_live = sum(1 for s in range(LIVE_HI + 1)
                      if (cell_read(plz, *cell(s, a.ncol)) == live[s]).all())
        if mode == 'probe':
            ok_pat = 0
            for s in range(LIVE_HI + 1, SLOT_HI + 1):
                okl, got, why = pattern_decode(cell_read(plz, *cell(s, a.ncol)))
                ok_pat += 1 if (okl and got == s) else 0
            if a.no_pattern:
                P('[R4 ] 回读 现役槽 == 基底: %d / %d %s ; (--no-pattern: 新槽留空)'
                  % (ok_live, LIVE_HI + 1, '✓' if ok_live == LIVE_HI + 1 else '✗'))
                assert ok_live == LIVE_HI + 1
            else:
                P('[R4 ] 回读 现役槽 == 基底: %d / %d ; 新槽图案解码: %d / %d %s'
                  % (ok_live, LIVE_HI + 1, ok_pat, SLOT_HI - LIVE_HI,
                     '✓' if ok_live == LIVE_HI + 1 and ok_pat == SLOT_HI - LIVE_HI else '✗'))
                assert ok_live == LIVE_HI + 1 and ok_pat == SLOT_HI - LIVE_HI
        else:
            ok_all = 0
            for s in range(SLOT_LO, SLOT_HI + 1):
                okl, got, why = pattern_decode(cell_read(plz, *cell(s, a.ncol)))
                ok_all += 1 if (okl and got == s) else 0
            P('[R4-allpat] 回读 **全部 %d 槽** 图案解码 == 槽号: %d %s'
              % (SLOT_HI + 1, ok_all, '✓' if ok_all == SLOT_HI + 1 else '✗'))
            assert ok_all == SLOT_HI + 1
        iz.close()
        if mode == 'probe':
            n_in, n_out, ex = compare_windows(dst, a.base, hdr_s['size'])
            P('[D  ] 全盘差异: 计划窗口内 %d B ; **窗口外 %d B** %s'
              % (n_in, n_out, '✓' if n_out == 0 else '✗ %s' % ex))
            assert n_out == 0, ex
    ib.close()
    ist.close()
    _save(tag, dict(dry=False, w=W, h=a.h, ncol_old=NCOL_OLD, ncol_new=a.ncol, tag=tag,
                    gate=[GATE_OLD, GATE_NEW], px_size=px_s, nseg=len(segs_new), payload=payload,
                    slots=[SLOT_LO, SLOT_HI], n_slots=SLOT_HI + 1,
                    live_slots=[0, LIVE_HI], n_live=LIVE_HI + 1, n_pattern=SLOT_HI - LIVE_HI,
                    nrow=nrow, cells=nrow * a.ncol, spare=nrow * a.ncol - SLOT_HI - 1,
                    base=os.path.relpath(a.base, REPO).replace('\\', '/'),
                    stage=os.path.relpath(a.stage, REPO).replace('\\', '/'),
                    out=os.path.relpath(a.out, REPO).replace('\\', '/'),
                    allpat=os.path.relpath(a.allpat_out, REPO).replace('\\', '/'),
                    sha256={os.path.basename(p): sha256_file(p)
                            for p in (a.stage, a.out, a.allpat_out, a.base)},
                    bytes={os.path.basename(p): os.path.getsize(p)
                           for p in (a.stage, a.out, a.allpat_out, a.base)},
                    elf_patch=[dict(va='0x%08X' % va, iso='0x%08X' % off, old='%08X' % w0,
                                    new='%08X' % w1, tag=tg) for (va, off, w0, w1, tg) in elf_patch],
                    rec_total=len(recs_ne), rec_safe=len(safe), rec_overlap=len(over),
                    rec_overlap_detail=[dict(face=f, idx=k, code=k + 0x20, u0=r[2], v0=r[3],
                                             u1=r[4], v1=r[5]) for (f, k, r) in over],
                    strip_rects=len(strip), strip_refs=sum(len(v) for v in strip.values()),
                    strip_texels=strip_texels, strip_kept=strip_kept,
                    strip_codes=['0x%02X' % codes[0], '0x%02X' % codes[-1]],
                    moved_live=moved, tail_outside_changed=outside))
    return 0


def compare_windows(out_iso, base_iso, img_size, extra=()):
    allow = ([(VA2ISO(COLS_VA), VA2ISO(COLS_VA) + 1)] if True else []) + \
            [(VA2ISO(v), VA2ISO(v) + 1) for v in ELF_SITES]
    allow += [(int(a), int(b)) for (a, b) in extra]      # ★ K2: 调用方可追加 ELF 站点窗口
    allow.append((MENU_BASE, MENU_BASE + img_size))
    allow.append((0x828D8, 0x828E0))
    allow.append((0x8000 + 80, 0x8000 + 88))
    so, sb = os.path.getsize(out_iso), os.path.getsize(base_iso)
    n_in = n_out = 0
    ex = []
    with open(out_iso, 'rb') as fo, open(base_iso, 'rb') as fb:
        pos = 0
        while pos < sb:
            n = min(1 << 22, sb - pos)
            bo, bb = fo.read(n), fb.read(n)
            if bo != bb:
                for i in range(n):
                    if bo[i] != bb[i]:
                        p = pos + i
                        if any(lo <= p < hi for (lo, hi) in allow):
                            n_in += 1
                        else:
                            n_out += 1
                            if len(ex) < 8:
                                ex.append((p, bb[i], bo[i]))
            pos += n
        if so > sb:
            fo.seek(sb)
            extra = fo.read(so - sb)
            nz = sum(1 for b in extra if b)
            n_out += nz
            if nz:
                ex.append(('tail', so - sb, nz))
    return n_in, n_out, ex


def _save(tag, extra):
    d = dict(extra=extra, log=LOG)
    with io.open(os.path.join(OUTDIR, 'cap_build_%s_report.json' % tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'cap_build_%s.log' % tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % os.path.join(OUTDIR, 'cap_build_%s_report.json' % tag))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
