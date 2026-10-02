#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..'))

r"""font_build.py — GR PS2 字库生成器: 字符表 → COMMON.PAK 新表面(仅像素差异) + FONT.RES 记录表(展开态/槽位态)

内核复用已实机验证的逻辑:
  - 布局/绘制/收割   = tmp\zh7_build.py (GR_ZH7 全量盘, 40000 帧 PASS)
  - FONT.RES DP 压缩 = ft_dpc.dp_compress (payload ≤ 4413B, 槽 4421B)
  - 展开态解析回环   = parse_faces / decode_entry 双自检

== 两种码位分配策略 ==
  dbcs 模式 (默认, = ZH7 路线, 需 ELF DBCS 补丁 SLUS_P_U 配合):
    字表字符分三类:
      single  — 单字节码位 (0xA4..0xFE 池, 避让保护区 {0xAE,0xB1,0xB5,0xE7,0xF1} 与 0xFF 槽)
      pair    — DBCS 标记对: 第 k 字 → (lead,trail) = (0xA1+k//94, 0xA1+k%94), 记录 idx = 224+k
      marker  — 标记字: 既有单字节码位被指定为 lead (默认 0xA1,0xA2,0xA3); 其"对形式"
                占 idx 381-383, 字形复用单字节格 (v5 ELF 标记制)
    face 预算: large rows5(160) + default rows12(384=224+160 DBCS) + huge rows7(112)
    atlas: 收割被裁撤记录格清底, 26px 带内排 16px 格, u0 = x-20 ≥ 1 (0xA1 诅咒规避)
  single 模式 (= ZH3/ZH5 路线, 无需 ELF 补丁):
    全部字符为 single, 重绘**既有记录的格** (Latin-1 重音格), FONT.RES 与记录矩形不动,
    仅改 COMMON.PAK 像素 —— 保守, 容量 ≤ 89 字。

== 输入 ==
  --charset charset.csv   列: char,strategy[,code]   (# 注释行; strategy ∈ single/pair/marker)
  --base-ft  字体展开态 (7222B; ZH7 用 zh6\ft_expanded_zh6.bin, 原版用 artifacts\font_rsfb_engine.bin)
  --base-pak COMMON.PAK (400,659B; ZH7 用 han_v2\COMMON_PAK_ZH6.bin, 原版用 artifacts\COMMON_PAK.bin)
  --ttf 字体文件 --size 像素 (默认 SimHei 16px)

== 输出 (--out-dir) ==
  COMMON_PAK_NEW.bin     仅表面像素差异 (差异白名单自检)
  FONT_RES_expanded.bin  展开态 (dbcs 模式; ≤7222B)
  FONT_RES_slot.bin      4421B 槽位态 = {plen}{7222}{DP payload}+00 填充 (dbcs 模式)
  charset_compiled.json  编译码表 (text_replace.py 的 --charset 输入)
  layout.txt             逐格布局表
  (single 模式: FONT_RES_* 不产出 —— 字体文件零改动)

== 校验 (全部 ELF 无关, 离线可判) ==
  parse_faces 回环 = 原样式表; decode_entry(槽) == 展开态; payload ≤ 4413;
  展开态 ≤ 7222; PAK 差异全部落在 0x1069 表面内; 新格 u0≥1 且互不重叠且避让保留矩形。
  宁少勿错: 字符数超容量 / 码位冲突 / 字表外字符 → 报错退出, 不产出半成品。

== 用法示例 ==
  python font_build.py --charset zh7_charset.csv --mode dbcs \
      --base-ft C:\gr_build\tmp\zh6\ft_expanded_zh6.bin \
      --base-pak han_v2\COMMON_PAK_ZH6.bin \
      --ttf D:\Document\Fonts\SimHei.ttf --size 16 --out-dir out\
"""
import argparse
import csv
import json
import os
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ft_dpc import dp_compress                    # noqa: E402
from lz77_decode import decode_entry              # noqa: E402

SURF = 0x1069                                     # COMMON.PAK 内 new_font_revised 表面
ATLAS = 512
FT_LIMIT = 7222                                   # FONT.RES 展开态槽 (real 字段)
SLOT_STORED = 4421                                # FONT.RES stored 槽
PAYLOAD_MAX = 4413                                # 槽内 payload 上限
PROTECTED = (0xAE, 0xB1, 0xB5, 0xE7, 0xF1)        # EN 在用: ® ± µ ç ñ
POISON = 0xFF                                     # 表尾 + huge 头, 禁写
MARK_CODES = (0xA1, 0xA2, 0xA3)                   # v5 ELF lead 标记码
ROWS = {'large': 5, 'default': 12, 'huge': 7}     # dbcs 模式 face 行数 (ZH7 配方)
CELL_W, CELL_H = 16, 26
ADV16 = 16


def die(msg):
    raise SystemExit('[font_build] FAIL: ' + msg)


# ---------------------------------------------------------- FONT.RES 结构

def parse_faces(ft):
    """展开态 FONT.RES → (faces, style_count, styles)。faces = [(name, 14×u32, 记录列表)]"""
    p = 0
    sl = struct.unpack_from('<I', ft, p)[0]
    p += 4 + sl
    n = struct.unpack_from('<I', ft, p)[0]
    p += 4
    faces = []
    for _ in range(n):
        l = struct.unpack_from('<I', ft, p)[0]
        p += 4
        nm = ft[p:p + l].decode('latin-1')
        p += l
        fld = list(struct.unpack_from('<14I', ft, p))
        p += 56
        nrec = fld[4] * fld[5]
        recs = [struct.unpack_from('<BB4H', ft, p + 10 * r) for r in range(nrec)]
        p += nrec * 10
        faces.append((nm, fld, recs))
    ns = struct.unpack_from('<I', ft, p)[0]
    p += 4
    return faces, ns, ft[p:]


def rect_of(rec):
    """10B 记录 (pad,adv,u0,v0,u1,v1) → atlas 采样矩形 (u 恒 +20, 引擎硬编码)。"""
    _pad, _adv, u0, v0, u1, v1 = rec
    return (u0 + 20, v0, u1 + 20, v1)


# ---------------------------------------------------------- 字表

def load_charset(path, mode):
    """→ singles: [(char, code|None)], pairs: [char], markers: [(char, code|None)]。
    校验字符唯一性 (marker 字只出现一次, 码位可显式给标记码)。"""
    singles, pairs, markers = [], [], []
    seen_char = {}
    with open(path, 'r', encoding='utf-8-sig') as f:
        rows = [ln.rstrip('\n') for ln in f if ln.strip() and not ln.startswith('#')]
    for ln_i, ln in enumerate(rows, 1):
        parts = [x.strip() for x in ln.split(',')]
        if ln_i == 1 and parts and parts[0].lower() == 'char':
            continue
        if not parts or not parts[0]:
            die('字表第 %d 行缺字符: %r' % (ln_i, ln))
        ch, strat = parts[0], (parts[1].lower() if len(parts) > 1 else 'single')
        code = int(parts[2], 0) if len(parts) > 2 and parts[2] else None
        if ch in seen_char:
            die('字表字符重复: %r (第 %d 行)' % (ch, seen_char[ch]))
        seen_char[ch] = ln_i
        if strat == 'single':
            singles.append((ch, code))
        elif strat == 'pair':
            if mode != 'dbcs':
                die('single 模式不允许 pair 字符: %r' % ch)
            pairs.append(ch)
        elif strat == 'marker':
            if mode != 'dbcs':
                die('single 模式不允许 marker 字符: %r' % ch)
            markers.append((ch, code))
        else:
            die('字表第 %d 行策略非法: %r (single/pair/marker)' % (ln_i, strat))
    return singles, pairs, markers


def alloc_single_codes(singles, n_markers):
    """单字节码位分配。显式 code 优先; 其余按字表顺序从空闲池贪心取。
    池 = 0xA1..0xFE − 保护区 − 标记码(A1-A3 预留给 marker 字)。宁少勿错。"""
    explicit = {}
    for ch, code in singles:
        if code is None:
            continue
        if not (0xA1 <= code <= 0xFE) or code == POISON:
            die('码位 0x%02X 不可用 (%r): 越界/0xFF 毒槽' % (code, ch))
        if code in PROTECTED:
            die('码位 0x%02X 是 EN 保护区 ®±µçñ (%r)' % (code, ch))
        if code in explicit.values():
            die('码位 0x%02X 显式重复 (%r)' % (code, ch))
        explicit[ch] = code
    pool = [c for c in range(0xA1, POISON) if c not in PROTECTED and c not in MARK_CODES]
    free = set(pool) - set(explicit.values())
    out = []
    cursor = 0
    for ch, code in singles:
        if code is not None:
            out.append((ch, code))
            continue
        while cursor < len(pool) and pool[cursor] not in free:
            cursor += 1
        if cursor >= len(pool):
            die('单字节码位池耗尽 (池 %d 格) — 宁少勿错, 请删减字表' % len(pool))
        out.append((ch, pool[cursor]))
        free.discard(pool[cursor])
    return out, sorted(free)


# ---------------------------------------------------------- atlas

def harvest(A, faces, rows):
    """收割被裁撤记录的格清底 (保留记录矩形避让)。→ (kept_rects, cleared)"""
    large_r, def_r, huge_r = faces[0][2], faces[1][2], faces[2][2]
    kept = []
    for c in range(0x20, 0x20 + 160):            # large rows5 = 0x20..0xBF
        kept.append(rect_of(large_r[c - 0x20]))
    for c in range(0x20, 0x100):
        if 0x7F <= c <= 0xA0 and c != 0x92:      # 占位虚线格 → 收割
            continue
        kept.append(rect_of(def_r[c - 0x20]))
    for c in range(0x20, 0x90):                  # huge rows7 = 0x20..0x8F
        kept.append(rect_of(huge_r[c - 0x20]))
    cands = []
    for c in range(0xC0, 0x100):
        cands.append(rect_of(large_r[c - 0x20]))
    for c in range(0x90, 0x100):
        cands.append(rect_of(huge_r[c - 0x20]))
    for c in range(0x7F, 0xA1):
        if c != 0x92:
            cands.append(rect_of(def_r[c - 0x20]))

    def inter(a, b):
        return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

    cleared = []
    for r in cands:
        if any(inter(r, k) for k in kept):
            continue
        x0, y0, x1, y1 = [max(0, v) for v in r]
        x1, y1 = min(ATLAS, x1), min(ATLAS, y1)
        if x1 <= x0 or y1 <= y0:
            continue
        A[y0:y1, x0:x1] = 31
        cleared.append((x0, y0, x1, y1))
    return kept, cleared


def free_runs(A, kept, y0, y1):
    blocked = np.zeros(ATLAS, dtype=bool)
    for (kx0, ky0, kx1, ky1) in kept:
        if ky0 < y1 and ky1 > y0:
            blocked[max(0, kx0):min(ATLAS, kx1)] = True
    ink = (A[y0:y1, :] != 31).any(axis=0)
    blocked |= ink
    runs, x = [], 21                              # u0 = x-20 ≥ 1 (0xA1 诅咒规避)
    while x < ATLAS:
        if blocked[x]:
            x += 1
            continue
        y = x
        while y < ATLAS and not blocked[y]:
            y += 1
        if y - x >= CELL_W:
            runs.append((x, y))
        x = y
    return runs


def place_cells(A, kept, count):
    """26px 带扫描 + 二维去重贪心 → [(y0, x)]。容量不足返回 None (宁少勿错)。"""
    placement = []
    for y0 in list(range(0, ATLAS - CELL_H, 13)):
        for (a, b) in free_runs(A, kept, y0, y0 + CELL_H):
            x = a
            while x + CELL_W <= b:
                placement.append((y0, x))
                x += CELL_W
    placement.sort(key=lambda t: (t[0], t[1]))
    chosen = []
    occ = np.zeros((ATLAS, ATLAS), dtype=bool)
    for (y0, x) in placement:
        if occ[y0:y0 + CELL_H, x:x + CELL_W].any():
            continue
        occ[y0:y0 + CELL_H, x:x + CELL_W] = True
        chosen.append((y0, x))
        if len(chosen) == count:
            return chosen
    return None


def draw_glyphs(A, chosen, chars, ttf, size):
    f = ImageFont.truetype(ttf, size)
    for (y0, x), ch in zip(chosen, chars):
        A[y0:y0 + CELL_H, x:x + CELL_W] = 31
        m = f.getmask(ch, mode='L')
        w, h = m.size
        if h > CELL_H or w > CELL_W:
            die('字形 %r 尺寸 %dx%d 超格 %dx%d' % (ch, w, h, CELL_W, CELL_H))
        ga = np.asarray(m, dtype=np.uint8).reshape(h, w)
        tx = np.where(ga > 128, 0, 31).astype(np.uint8)
        py = y0 + (CELL_H - h) // 2
        A[py:py + h, x:x + w] = tx


# ---------------------------------------------------------- 主流程

def build_dbcs(a):
    ft = open(a.base_ft, 'rb').read()
    faces, ns, styles = parse_faces(ft)
    if [f[0] for f in faces] != ['large', 'default', 'huge']:
        die('base-ft face 顺序异常: %s' % [f[0] for f in faces])
    large_f, def_f, huge_f = faces
    singles, pairs, markers = load_charset(a.charset, 'dbcs')

    # 标记字: 码位必须落在标记码上 (可显式给, 否则按序自动占 A1/A2/A3)
    free_marks = list(MARK_CODES)
    mk = {}
    for ch, code in markers:
        if code is None:
            if not free_marks:
                die('标记码 A1-A3 已用尽, marker 字 %r 无法分配' % ch)
            code = free_marks.pop(0)
        else:
            if code not in MARK_CODES:
                die('marker 字 %r 的码位 0x%02X 不在标记码 %s 内'
                    % (ch, code, ['0x%02X' % c for c in MARK_CODES]))
            if code in free_marks:
                free_marks.remove(code)
            elif code in mk.values():
                die('标记码 0x%02X 重复使用 (%r)' % (code, ch))
        mk[ch] = code
    # 单字节码位分配 (marker 字同时进入单字节码表, 与 ZH6/ZH7 字表一致)
    singles2, free_pool = alloc_single_codes(singles, len(markers))
    codes = {ch: c for ch, c in singles2}
    codes.update(mk)
    # 对分配: (lead,trail) = (0xA1+k//94, 0xA1+k%94), idx=224+k; 标记字对占 381-383
    pair_of = {}
    if len(pairs) > 188:
        die('pair 字 %d > 188 (idx 224..383 = 160 新格 + 3 标记格) — 宁少勿错' % len(pairs))
    if len(pairs) + len(markers) > 160:
        die('pair %d + marker %d > 160 格 — 宁少勿错' % (len(pairs), len(markers)))
    for k, ch in enumerate(pairs):
        pair_of[ch] = (0xA1 + k // 94, 0xA1 + k % 94)
    marker_chars = [ch for ch, c in sorted(mk.items(), key=lambda kv: kv[1])]
    for j, ch in enumerate(marker_chars):
        pair_of[ch] = (0xA2, 0xE0 + j)

    # ---------- 1) FONT.RES 重排 ----------
    out = bytearray()
    out += struct.pack('<I', 20) + ft[4:24]        # {u32 20}{"new_font_revised.rsb"}
    out += struct.pack('<I', 3)
    tbl_off = {}
    for nm, fld, recs in faces:
        rows = ROWS[nm]
        l = len(nm)
        out += struct.pack('<I', l) + nm.encode()
        fld = list(fld)
        fld[5] = rows
        tbl_off[nm] = len(out) + 56
        out += struct.pack('<14I', *fld)
        nrec = fld[4] * rows
        for i in range(nrec):
            if i < len(recs):
                out += struct.pack('<BB4H', *recs[i])
            else:
                out += struct.pack('<BB4H', 0, 10, 0, 0, 0, 0)
    out += struct.pack('<I', ns) + styles
    dbcs_foff = tbl_off['default'] + 224 * 10
    if dbcs_foff + 160 * 10 > tbl_off['huge']:
        die('DBCS 记录区越过 huge face 头 (%d > %d)' % (dbcs_foff + 1600, tbl_off['huge']))

    # ---------- 2) atlas 收割 + 排格 + 绘制 ----------
    pak = bytearray(open(a.base_pak, 'rb').read())
    base_pak = bytes(pak)
    A = np.frombuffer(bytes(pak[SURF:SURF + ATLAS * ATLAS]),
                      dtype=np.uint8).reshape(ATLAS, ATLAS).copy()
    kept, cleared = harvest(A, faces, ROWS)
    new_chars = pairs[:]                            # 新格字符
    chosen = place_cells(A, kept, len(new_chars))
    if chosen is None:
        die('atlas 容量不足 %d 格 — 宁少勿错' % len(new_chars))
    draw_glyphs(A, chosen, new_chars, a.ttf, a.size)
    pak[SURF:SURF + ATLAS * ATLAS] = A.tobytes()

    # PAK 差异白名单 = 表面内
    diff = [i for i in range(min(len(base_pak), len(pak))) if base_pak[i] != pak[i]]
    bad = [i for i in diff if not (SURF <= i < SURF + ATLAS * ATLAS)]
    if bad or len(pak) != len(base_pak):
        die('PAK 差异越出表面: %d 处 (首 0x%X)' % (len(bad), bad[0] if bad else 0))

    # ---------- 3) DBCS 记录 ----------
    dbcs_recs = []
    for (y0, x) in chosen:
        dbcs_recs.append((0, ADV16, x - 20, y0, x - 20 + CELL_W, y0 + CELL_H))
    def_r = def_f[2]
    for j, ch in enumerate(marker_chars):
        rec = def_r[mk[ch] - 0x20]
        dbcs_recs.append((rec[0], rec[1], rec[2], rec[3], rec[4], rec[5]))
    if len(dbcs_recs) > 160:
        die('DBCS 记录 %d > 160' % len(dbcs_recs))
    for k, rec in enumerate(dbcs_recs):
        struct.pack_into('<BB4H', out, dbcs_foff + 10 * k, *rec)
    expanded = bytes(out)

    # ---------- 4) 校验 (ELF 无关) ----------
    if len(expanded) > FT_LIMIT:
        die('FONT.RES 展开态 %d > %d' % (len(expanded), FT_LIMIT))
    f2, ns2, st2 = parse_faces(expanded)
    if [x[0] for x in f2] != ['large', 'default', 'huge'] or st2 != styles or ns2 != ns:
        die('FONT.RES 解析回环失败')
    if [f2[i][1][5] for i in range(3)] != [ROWS['large'], ROWS['default'], ROWS['huge']]:
        die('行数回写回环失败')
    payload = dp_compress(expanded)
    if len(payload) > PAYLOAD_MAX:
        die('DP payload %d > %d — 字表过大或字形结构异常' % (len(payload), PAYLOAD_MAX))
    frame = struct.pack('<II', len(payload), len(expanded)) + payload
    slot = frame + b'\x00' * (SLOT_STORED - len(frame))
    back, stats = decode_entry(slot)
    if back != expanded or any(s[3] for s in stats):
        die('槽回环失败')
    return dict(pak=bytes(pak), expanded=expanded, slot=slot,
                codes=codes, pair_of=pair_of, markers=marker_chars,
                chosen=chosen, pairs=pairs, cleared=cleared,
                layout_extra=[(381 + j, ch, pair_of[ch], '复用单字节格')
                              for j, ch in enumerate(marker_chars)])


# ---------------------------------------------------------- v6 (T3 12px 混排, ZH8 实战配方)

V6_ROWS = {'large': 5, 'default': 7, 'huge': 6}   # huge 16列 → 0x20-0x7F
V6_EN_CODES = list(range(0x20, 0x7F)) + [0x92, 0xAE, 0xB1, 0xB5, 0xE7, 0xF1]
V6_X0 = 20                                        # 记录坐标系原点 (采样 x = rec.u0 + 20, ZH7b/ZH8 实证)


def build_v6(a):
    """T3 终局: 12px Zpix 网格 (直 UV) + EN 三 face 共享格 — ZH8/ZH11 实战配方。

    ★边缘留白铁律 (ZH11, FONT_CAPACITY.md §十):
      --grid-cols 37 --cell-w 13 --margin 1 --grid-y 128 --en-y 445 --ch 15
      - pitch(cell-w) ≥ 墨宽 + 2*margin: 格间左右各 ≥1px 留白 (GS 双线性 quad 边缘
        半 texel 溢出采样域 [x-1, x+pitch) 全空白 → 邻格墨不可达);
      - 格内内缩 margin: 字形画在 [x+margin, x+margin+iw);
      - 清底只清 rows 128-511 (rows 0-127 = CLUT + 禁写区, 覆写即挂死);
      - EN 两行间隔 1px (en_y + CH + 1), 杜绝上一行底缘溢出采到下一行顶墨;
      - 逐格采样域自检: quad [x-1, x+pitch) × [y-1, y+CH+1) 内非本格墨 = 0。
    charset JSON: {"singles": {字: 码}, "pair_of": {字: [lead, trail]}}。"""
    cs = json.load(open(a.charset if a.charset.endswith('.json') else a.charset, encoding='utf-8'))
    singles = {k: int(v) for k, v in cs['singles'].items()}
    pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
    margin = getattr(a, 'margin', 1)
    ink_max = a.cell_w - 2 * margin
    if ink_max < 8:
        die('margin 过大: 墨预算 %d < 8' % ink_max)
    ncol, cw, chh, gy = a.grid_cols, a.cell_w, a.cell_h, a.grid_y
    CH = a.ch
    en_y = a.en_y
    if V6_X0 + ncol * cw > 512:
        die('网格 %d 列 × %d 越界 (%d > 512)' % (ncol, cw, V6_X0 + ncol * cw))
    ft = open(a.base_ft, 'rb').read()
    faces, ns, styles = parse_faces(ft)
    if [f[0] for f in faces] != ['large', 'default', 'huge']:
        die('base-ft face 顺序异常')
    def_r = faces[1][2]
    pak = bytearray(open(a.base_pak, 'rb').read())
    A = np.frombuffer(bytes(pak[SURF:SURF + ATLAS * ATLAS]),
                      dtype=np.uint8).reshape(ATLAS, ATLAS).copy()
    # 1) 提取 EN 墨块 (清底之前)
    glyphs = {}
    for c in V6_EN_CODES:
        _p, _a, u0, v0, u1, v1 = def_r[c - 0x20]
        patch = A[v0:v1, u0 + V6_X0:u1 + V6_X0]
        ink = np.argwhere(patch != 31)
        if len(ink) == 0:
            glyphs[c] = None
            continue
        yy0, yy1 = int(ink[:, 0].min()), int(ink[:, 0].max()) + 1
        xx0, xx1 = int(ink[:, 1].min()), int(ink[:, 1].max()) + 1
        top, bot = 6, min(max(21, yy1), 6 + 17)          # 基线=19, 带 ≤17
        sub = np.where(patch[top:bot, xx0:xx1] < 16, 0, 31).astype(np.uint8)
        if sub.shape[0] > CH:                             # 高墨纵向最近邻压到 CH
            sub = np.asarray(Image.fromarray(sub, 'L').resize(
                (sub.shape[1], CH), Image.NEAREST), dtype=np.uint8)
        glyphs[c] = (sub, int(xx1 - xx0), int(sub.shape[0]))
    # 2) 清底 — ★rows 0-127 = CLUT(rows0-1) + 禁写区(2-127), 只清 128-511
    A[128:ATLAS, :] = 31
    # 3) EN 两行 (en_y, en_y+CH+1 — 行间 1px 缝), 格 = 墨宽+1, adv = 墨宽 (原版约定)
    en_rect = {}
    order = sorted((c for c in V6_EN_CODES if glyphs[c]), key=lambda c: -glyphs[c][2])
    x, rowi = V6_X0, 0
    for c in order:
        sub, iw, _ih = glyphs[c]
        if x + iw + 1 > ATLAS - 1:                        # 右缘留 1 texel 空白 (右溢保护)
            rowi += 1
            x = V6_X0
        if rowi * (CH + 1) + en_y + CH > ATLAS:
            die('EN 行溢出纹理')
        y = en_y + rowi * (CH + 1)
        A[y:y + CH, x:x + iw] = sub
        en_rect[c] = (x - V6_X0, y, x - V6_X0 + iw, y + CH, iw)
        x += iw + 1
    # 4) CJK 网格 (pitch + 格内 margin 内缩)
    zp = ImageFont.truetype(a.ttf, a.size)
    sh = ImageFont.truetype(a.ttf_fallback, a.size) if getattr(a, 'ttf_fallback', None) else None

    def render(ch):
        for fnt in (zp, sh) if sh is not None else (zp,):
            img = Image.new('L', (20, 20), 255)
            d = ImageDraw.Draw(img)
            d.text((3, 3), ch, font=fnt, fill=0)
            arr = np.asarray(img)
            ink = arr < 128
            if not ink.any():
                continue
            ys, xs = np.where(ink)
            yy0, yy1, xx0, xx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            if xx1 - xx0 > ink_max or yy1 - yy0 > 12:
                continue
            return np.where(ink[yy0:yy1, xx0:xx1], 0, 31).astype(np.uint8)
        die('字 %r 无法渲染 (墨宽 > %d)' % (ch, ink_max))
    order = sorted(pair_of, key=lambda ch: (pair_of[ch][0], pair_of[ch][1]))
    single_chars = sorted(singles, key=lambda ch: singles[ch])
    slots = order + single_chars
    need_rows = (len(slots) + ncol - 1) // ncol
    if gy + need_rows * chh > en_y:
        die('网格 %d 行超出 EN 区 (y=%d)' % (need_rows, en_y))
    cjk_rect = {}
    cjk_xy = {}
    for k, ch in enumerate(slots):
        col, row = k % ncol, k // ncol
        x0 = V6_X0 + cw * col
        y0 = gy + chh * row
        p = render(ch)
        ih, iw = p.shape
        if iw + 2 * margin > cw:
            die('字 %r 墨宽 %d 超 pitch 内缩预算 %d' % (ch, iw, cw - 2 * margin))
        A[y0 + (chh - 2 - ih):y0 + (chh - 2), x0 + margin:x0 + margin + iw] = p
        cjk_rect[ch] = (x0 - V6_X0, y0, x0 - V6_X0 + cw, y0 + chh, cw)
        cjk_xy[ch] = (x0, y0, iw, ih)
    # 4b) 逐格采样域自检 (GS 双线性溢出域 [x-1, x+cw+1) × [y-1, y+CH+1) 非本格墨 = 0)
    ink_total = A != 31
    bad_cells = []
    for k, ch in enumerate(slots):
        x0, y0, iw, ih = cjk_xy[ch]
        mx0, my0 = x0 + margin, y0 + (chh - 2 - ih)
        dom = ink_total[y0 - 1:y0 + chh + 1, x0 - 1:x0 + cw + 1]
        mask = np.ones(dom.shape, dtype=bool)
        mask[my0 - (y0 - 1):my0 - (y0 - 1) + ih,
             mx0 - (x0 - 1):mx0 - (x0 - 1) + iw] = False
        if int(dom[mask].sum()):
            bad_cells.append((ch, k))
    if bad_cells:
        die('采样域渗墨格 %d: %s' % (len(bad_cells), bad_cells[:8]))
    # 5) FONT.RES
    space_rec = (0, 10, 41, 104, 52, 130)
    code2char = {code: ch for ch, code in singles.items()}
    out = bytearray()
    out += struct.pack('<I', 20) + ft[4:24]
    out += struct.pack('<I', 3)
    for nm in ('large', 'default', 'huge'):
        fld = list(faces[{'large': 0, 'default': 1, 'huge': 2}[nm]][1])
        fld[1] = CH
        fld[5] = V6_ROWS[nm]
        out += struct.pack('<I', len(nm)) + nm.encode()
        out += struct.pack('<14I', *fld)
        recs = []
        lo, hi = {'large': (0x20, 0xC0), 'default': (0x20, 0x100), 'huge': (0x20, 0x80)}[nm]
        for c in range(lo, hi):
            if c in en_rect:
                u0, v0, u1, v1, adv = en_rect[c]
                recs.append((0, adv, u0, v0, u1, v1))
            elif nm == 'default' and c in code2char:
                u0, v0, u1, v1, adv = cjk_rect[code2char[c]]
                recs.append((0, adv, u0, v0, u1, v1))
            else:
                recs.append(space_rec)
        for r in recs:
            out += struct.pack('<BB4H', *r)
    out += struct.pack('<I', ns) + styles
    expanded = bytes(out)
    if len(expanded) > FT_LIMIT:
        die('展开态 %d > %d' % (len(expanded), FT_LIMIT))
    payload = dp_compress(expanded, verbose=False)
    if len(payload) > PAYLOAD_MAX:
        die('payload %d > %d' % (len(payload), PAYLOAD_MAX))
    frame = struct.pack('<II', len(payload), len(expanded)) + payload
    slot = frame + b'\x00' * (SLOT_STORED - len(frame))
    back, _st = decode_entry(slot)
    if back != expanded:
        die('槽回环失败')
    pak[SURF:SURF + ATLAS * ATLAS] = A.tobytes()
    lines = ['# v6 layout CH=%d cols=%d pitch=%dx%d grid_y=%d margin=%d en_y=%s ink_max=%d'
             % (CH, ncol, cw, chh, gy, margin, en_y, ink_max)]
    for k, ch in enumerate(slots):
        u0, v0, u1, v1, adv = cjk_rect[ch]
        if ch in pair_of:
            tag = 'pair(%02X,%02X)' % pair_of[ch]
        else:
            tag = 'single 0x%02X' % singles[ch]
        lines.append('slot=%d %s %s cell=(%d,%d) rec=(%d,%d,%d,%d,%d)'
                     % (k, ch, tag, u0 + V6_X0, v0, u0, v0, u1, v1, adv))
    for c in sorted(en_rect):
        u0, v0, u1, v1, adv = en_rect[c]
        lines.append('EN %02X rec=(%d,%d,%d,%d) adv=%d' % (c, u0, v0, u1, v1, adv))
    return dict(pak=bytes(pak), expanded=expanded, slot=slot, codes=singles,
                pair_of=pair_of, markers=[], chosen=[], pairs=[], cleared=[],
                layout_extra=[], layout_lines=lines,
                grid=dict(ncol=ncol, cw=cw, ch=chh, gridy=gy, margin=margin,
                          x0=V6_X0, en_y=[en_y, en_y + CH + 1], ink_max=ink_max))


# ---------------------------------------------------------- v7 (ZH12 face 恢复矩阵配方)

V7_X0 = 20                                        # 记录坐标系原点 (采样 x = rec.u0 + 20)


def build_v7(a):
    """ZH12 配方 (FONT_CAPACITY.md §十一): face 恢复矩阵 + EN 原版墨迹窗口拷贝。

    ★ large face + atlas rows 0-131 = 原版字节 verbatim (采样域全在 rows 2-131);
      default/huge face CH=17 (与 cave CELL_H 一致 → Controller 标签对字 1:1), Y0=130。
    ★ CJK 网格: pair 按码位槽稀疏保留 (格 = slot→(col=slot%%NCOL, row=slot//NCOL)),
      single 填末两行空格 + 被裁 pair 的孔位格 (码位域零重编码)。
    ★ EN 101 码位 = 原版墨迹窗口拷贝 (窗口 = 原记录 v0+6 起 17 行, 逐列 %%512 wrap),
      排到 S 带 [en_band_a, +17)/[en_band_b, +17), 记录 v0 = S-2 (dv=2 采样补偿)。
    ★ single 记录铁律 (ZH12 修订): default face 的 single 码位记录必须按「码位逆映射」
      指向其网格格 —— chr(c) 字符匹配恒假曾致 76 记录全落空格记录 → single 全空白。

    输入: --charset *.json (charset_compiled: pair_of+codes 码位沿用), --trim (裁字表)。
    配套 cave 常量 (SLUS_P_V10.elf): NCOL=37 CELL_W=13 CELL_H=17 Y0=130 = 本模式默认。"""
    if not a.charset.endswith('.json'):
        die('v7 模式 --charset 需要 charset_compiled_*.json (含 pair_of+codes)')
    cs = json.load(open(a.charset, encoding='utf-8'))
    pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
    singles = {k: int(v) for k, v in cs['codes'].items()}
    trim = set(json.load(open(a.trim, encoding='utf-8'))['trim19']) if a.trim else set()
    margin = getattr(a, 'margin', 1)
    ncol, cw, chh, gy = a.grid_cols, a.cell_w, a.ch, a.grid_y
    X0 = V7_X0
    en_a, en_b = a.en_band_a, a.en_band_b
    if X0 + ncol * cw > ATLAS:
        die('网格 %d 列 × %d 越界' % (ncol, cw))
    ft = open(a.base_ft, 'rb').read()
    F0, ns, styles = parse_faces(ft)
    if [f[0] for f in F0] != ['large', 'default', 'huge']:
        die('base-ft face 顺序异常')
    pak0 = bytearray(open(a.base_pak, 'rb').read())
    ORIG = np.frombuffer(bytes(pak0[SURF:SURF + ATLAS * ATLAS]),
                         dtype=np.uint8).reshape(ATLAS, ATLAS).copy()
    A = ORIG.copy()
    A[132:ATLAS, :] = 31                          # rows 0-131 原样恢复, 其余清底

    zp = ImageFont.truetype(a.ttf, a.size)
    sh = ImageFont.truetype(a.ttf_fallback, a.size) if getattr(a, 'ttf_fallback', None) else None

    def render(ch):
        for fnt in (zp, sh) if sh is not None else (zp,):
            img = Image.new('L', (20, 20), 255)
            d = ImageDraw.Draw(img)
            d.text((3, 3), ch, font=fnt, fill=0)
            arr = np.asarray(img)
            ink = arr < 128
            if not ink.any():
                continue
            ys, xs = np.where(ink)
            yy0, yy1, xx0, xx1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            ih, iw = yy1 - yy0, xx1 - xx0
            if iw > cw - 2 * margin or ih > 12:
                continue
            return np.where(ink[yy0:yy1, xx0:xx1], 0, 31).astype(np.uint8), ih, iw
        die('字 %r 无法渲染 (墨超 %dx%d 预算)' % (ch, cw - 2 * margin, 12))

    kept_pairs = {k: v for k, v in pair_of.items() if k not in trim}
    # 1) CJK pair 格 (码位稀疏保留)
    pair_cells = {}
    for ch, (l, t) in kept_pairs.items():
        slot = (l - 0xA1) * 94 + (t - 0xA1)
        col, row = slot % ncol, slot // ncol
        x, y = X0 + cw * col, gy + chh * row
        if y + chh >= en_a:
            die('pair slot %d 越入 EN 带' % slot)
        p, ih, iw = render(ch)
        A[y + chh - 2 - ih:y + chh - 2, x + margin:x + margin + iw] = p
        pair_cells[ch] = (x, y, iw, ih, slot)
    # 2) single 格: pair 末行尾段 + 下一整行 + 被裁孔位
    holes = sorted((l - 0xA1) * 94 + (t - 0xA1) for k, (l, t) in pair_of.items() if k in trim)
    max_slot = max(s for _k, (_l, _t) in kept_pairs.items()
                   for s in [(_l - 0xA1) * 94 + (_t - 0xA1)])
    last_row = max_slot // ncol
    free_cells = [(X0 + cw * c, gy + chh * last_row) for c in range(max_slot % ncol + 1, ncol)]
    free_cells += [(X0 + cw * c, gy + chh * (last_row + 1)) for c in range(ncol)]
    free_cells += [(X0 + cw * (s % ncol), gy + chh * (s // ncol)) for s in holes]
    if len(free_cells) < len(singles):
        die('single 格预算 %d < %d' % (len(free_cells), len(singles)))
    single_cells = {}
    for ch, (x, y) in zip(sorted(singles, key=lambda k: singles[k]), free_cells):
        p, ih, iw = render(ch)
        A[y + chh - 2 - ih:y + chh - 2, x + margin:x + margin + iw] = p
        single_cells[ch] = (x, y, iw, ih)
    code2single = {code: ch for ch, code in singles.items()}
    assert len(code2single) == len(singles)
    # 3) EN 原版墨迹窗口拷贝带 (S 带 A/B, 记录 v0 = S-2)
    drec0 = F0[1][2]
    used_en = list(range(0x20, 0x7F)) + [0x92, 0xAE, 0xB1, 0xB5, 0xE7, 0xF1]
    groups = {}
    for c in used_en:
        _t, _adv, u0, v0, u1, v1 = drec0[c - 0x20]
        if v1 - v0 != 26 or v0 not in (104, 130, 156, 182, 208):
            die('EN 码位 %02X 原记录非标准组 (v0=%d v1=%d)' % (c, v0, v1))
        groups.setdefault(v0, []).append(c)
    order = [c for v0 in sorted(groups) for c in groups[v0]]
    en_cells = {}
    en_rec_v = {'A': en_a - 2, 'B': en_b - 2}
    x, band = X0, 'A'
    for c in order:
        _t, adv, u0, v0, u1, v1 = drec0[c - 0x20]
        w = u1 - u0
        if x + w > ATLAS - 1:
            band = 'B' if band == 'A' else None
            if band is None:
                die('EN 带溢出')
            x = X0
        sy = en_a if band == 'A' else en_b
        src_cols = [(u0 + X0 + k) % ATLAS for k in range(w)]
        A[sy:sy + chh, x:x + w] = ORIG[np.ix_(range(v0 + 6, v0 + 6 + chh), src_cols)]
        en_cells[c] = (x, w, band, adv)
        x += w
    en_tail_x = x
    clash = sorted(set(code2single) & set(en_cells))
    if clash:
        die('single 码位与 EN 带冲突: %s' % [hex(c) for c in clash])
    # 4) FONT.RES (large verbatim / default+huge CH17 / single 码位逆映射)
    def space_rec():
        w = min(11, ATLAS - en_tail_x - 2)
        xx = en_tail_x + 1
        return (0, 10, xx - X0, en_b - 2, xx - X0 + w, en_b - 2 + chh)
    srec = space_rec()
    out = bytearray()
    out += struct.pack('<I', 20) + ft[4:24]
    out += struct.pack('<I', 3)
    for fi, nm in ((0, 'large'), (1, 'default'), (2, 'huge')):
        fld = list(F0[fi][1])
        if nm != 'large':
            fld[1] = chh
        if nm == 'huge':
            fld[4], fld[5] = 16, 6
        recs = []
        if nm == 'large':
            # verbatim 基础上, 仅 CJK single 码位 → 网格格 (ticker 等 large-face 元素;
            # ASCII/图标域逐字节原版保留) — 与 zh12_font.py 同步, v7 对账铁律
            for c in range(0x20, 0x100):
                if c in code2single:
                    xx, y, iw, ih = single_cells[code2single[c]]
                    recs.append((0, cw, xx - X0, y, xx - X0 + cw, y + chh))
                else:
                    recs.append(tuple(F0[0][2][c - 0x20]))
        elif nm == 'default':
            for c in range(0x20, 0x100):
                if c in en_cells:
                    xx, w, band_, adv = en_cells[c]
                    recs.append((0, adv, xx - X0, en_rec_v[band_],
                                 xx - X0 + w, en_rec_v[band_] + chh))
                elif c in code2single:
                    xx, y, iw, ih = single_cells[code2single[c]]
                    recs.append((0, cw, xx - X0, y, xx - X0 + cw, y + chh))
                else:
                    recs.append(srec)
        else:
            for c in range(0x20, 0x80):
                if c in en_cells:
                    xx, w, band_, adv = en_cells[c]
                    recs.append((0, adv, xx - X0, en_rec_v[band_],
                                 xx - X0 + w, en_rec_v[band_] + chh))
                else:
                    recs.append(srec)
        if len(recs) != fld[4] * fld[5]:
            die('%s 记录数 %d != fld[4]*fld[5]=%d' % (nm, len(recs), fld[4] * fld[5]))
        out += struct.pack('<I', len(nm)) + nm.encode()
        out += struct.pack('<14I', *fld)
        for r in recs:
            out += struct.pack('<BB4H', *r)
    out += struct.pack('<I', ns) + styles
    expanded = bytes(out)
    if len(expanded) > FT_LIMIT:
        die('展开态 %d > %d' % (len(expanded), FT_LIMIT))
    # 5) 自检: single 记录 = 网格格 (防回归) / 采样域渗墨 / EN 逐位 / 槽回环
    F2, ns2, st2 = parse_faces(expanded)
    if ns2 != ns or st2 != styles:
        die('样式表回环失败')
    for c, ch in code2single.items():
        xx, y, iw, ih = single_cells[ch]
        r = F2[1][2][c - 0x20]
        if tuple(r) != (0, cw, xx - X0, y, xx - X0 + cw, y + chh):
            die('single 码位 %02X 记录未指向网格格: %r' % (c, r))
    for c, (xx, w, band_, _adv) in en_cells.items():
        _t, _adv, u0, v0, u1, v1 = drec0[c - 0x20]
        sy = en_a if band_ == 'A' else en_b
        src_cols = [(u0 + X0 + k) % ATLAS for k in range(w)]
        if not (A[sy:sy + chh, xx:xx + w] == ORIG[np.ix_(range(v0 + 6, v0 + 6 + chh), src_cols)]).all():
            die('EN 码位 %02X 窗口拷贝失真' % c)
    inkm = A != 31
    if inkm[en_a - 3:en_a, :].any() or inkm[en_b - 2:en_b, :].any() or inkm[130:133, :].any():
        die('带间/底缘空白被侵')
    allg = [(ch, pair_cells[ch][0], pair_cells[ch][1], pair_cells[ch][2], pair_cells[ch][3])
            for ch in pair_cells]
    allg += [(ch, single_cells[ch][0], single_cells[ch][1], single_cells[ch][2],
              single_cells[ch][3]) for ch in single_cells]
    bad_cells = []
    for ch, x, y, iw, ih in allg:
        mx0, my0 = x + margin, y + (chh - 2 - ih)
        dom = inkm[y + 1:y + chh + 3, x - 1:x + cw + 1]
        mask = np.ones(dom.shape, dtype=bool)
        mask[my0 - (y + 1):my0 - (y + 1) + ih, mx0 - (x - 1):mx0 - (x - 1) + iw] = False
        if int(dom[mask].sum()):
            bad_cells.append(ch)
    if bad_cells:
        die('采样域渗墨格 %d: %s' % (len(bad_cells), bad_cells[:8]))
    payload = dp_compress(expanded, verbose=False)
    if len(payload) > PAYLOAD_MAX:
        die('payload %d > %d' % (len(payload), PAYLOAD_MAX))
    frame = struct.pack('<II', len(payload), len(expanded)) + payload
    slot = frame + b'\x00' * (SLOT_STORED - len(frame))
    back, _st = decode_entry(slot)
    if back != expanded:
        die('槽回环失败')
    pak0[SURF:SURF + ATLAS * ATLAS] = A.tobytes()
    lines = ['# v7 layout CH=%d grid=(%d cols x %d rows) pitch=%dx%d y0=%d margin=%d en=%s dv=2'
             % (chh, ncol, (max_slot // ncol) + 2, cw, chh, gy, margin, [en_a, en_b])]
    for ch in kept_pairs:
        x, y, iw, ih, s = pair_cells[ch]
        lines.append('pair %s slot=%d cell=(%d,%d) ink=%dx%d rec=(%d,%d,%d,%d) adv=%d'
                     % (ch, s, x, y, iw, ih, x - X0, y, x - X0 + cw, y + chh, cw))
    for ch in single_cells:
        x, y, iw, ih = single_cells[ch]
        lines.append('single %s code=0x%02X cell=(%d,%d) ink=%dx%d rec=(%d,%d,%d,%d) adv=%d'
                     % (ch, singles[ch], x, y, iw, ih, x - X0, y, x - X0 + cw, y + chh, cw))
    for c in sorted(en_cells):
        xx, w, band_, adv = en_cells[c]
        lines.append('EN %02X band=%s x=%d w=%d rec_v0=%d adv=%d' % (c, band_, xx, w, en_rec_v[band_], adv))
    return dict(pak=bytes(pak0), expanded=expanded, slot=slot, codes=singles,
                pair_of={k: list(v) for k, v in kept_pairs.items()},
                markers=[], chosen=[], pairs=[], cleared=[], layout_extra=[],
                layout_lines=lines,
                grid=dict(ncol=ncol, cw=cw, ch=chh, gridy=gy, margin=margin,
                          x0=X0, en_y=[en_a, en_b], dv=2, trim=sorted(trim)))


# ---------------------------------------------------------- v8 (ZH13 拉丁 Zpix 重绘 + em-strip)

V8_X0 = 20                                        # 记录坐标系原点 (采样 x = rec.u0 + 20)
V8_EN_REDRAW = list(range(0x21, 0x7F)) + [0x92, 0xAE, 0xE7, 0xF1]   # 98 码位 (B1/B5=图标不动)
V8_EN_SRC = {0x92: '\u2019', 0xAE: '\u00AE', 0xE7: '\u00E7', 0xF1: '\u00F1'}
V8_KBD = set(range(0x41, 0x5B)) | set(range(0x30, 0x3A)) | {0x5F, 0x2E, 0x21, 0x23, 0x40, 0x2D, 0x3F, 0x24}


def build_v8(a):
    """ZH13 配方 (FONT_CAPACITY.md §十二): 拉丁 Zpix 12px 整体重绘 + CJK em-strip 垂直修复。

    ★ CJK 网格 CH=16 (rows 130..449, 释放行带给拉丁三带); 墨 = 画布 rows[3,17) 的
      **em-strip 整体放置** @ [y+3, y+17) (ink rel 底=13 的字上移 1px) — 保留字形在
      em 内的自然垂直位置 (修 ZH12「一」→「_」: 墨迹 bbox 裁剪+底锚丢 em 位置)。
    ★ default EN 98 码位 = Zpix 重绘 @ A/B 带 (S=452/468, 16 行带, 记录 v0=S-2,
      strip=[S+2,S+15), pitch=墨宽+2, ink@x+1); huge 96 记录 alias (fld[1]=16)。
    ★ large 键盘 43 码位 (A-Z 0-9 _ . ! # @ - ?) = Zpix @ C 带 (v0=482, 26 行 =
      large fld[1] → 1:1); large 其余 verbatim + CJK single 码位→网格 (ZH12 铁律)。
    ★ 配套 cave 常量 (SLUS_P_V11.elf): NCOL=37 CELL_W=13 CELL_H=16 Y0=130 = 本模式默认。"""
    if not a.charset.endswith('.json'):
        die('v8 模式 --charset 需要 charset_compiled_*.json (含 pair_of+codes)')
    cs = json.load(open(a.charset, encoding='utf-8'))
    kept_pairs = {k: tuple(v) for k, v in cs['pair_of'].items()}   # 已裁实存 pair
    singles = {k: int(v) for k, v in cs['codes'].items()}
    margin = getattr(a, 'margin', 1)
    ncol, cw, chh, gy = a.grid_cols, a.cell_w, a.ch, a.grid_y
    X0 = V8_X0
    en_a, en_b = a.en_band_a, a.en_band_b
    kbd_v0, kbd_v1 = getattr(a, 'kbd_v0', 482), getattr(a, 'kbd_v1', 508)
    kbd_strip = kbd_v0 + 6
    if X0 + ncol * cw > ATLAS:
        die('网格 %d 列 × %d 越界' % (ncol, cw))
    ft = open(a.base_ft, 'rb').read()
    F0, ns, styles = parse_faces(ft)
    if [f[0] for f in F0] != ['large', 'default', 'huge']:
        die('base-ft face 顺序异常')
    pak0 = bytearray(open(a.base_pak, 'rb').read())
    ORIG = np.frombuffer(bytes(pak0[SURF:SURF + ATLAS * ATLAS]),
                         dtype=np.uint8).reshape(ATLAS, ATLAS).copy()
    A = ORIG.copy()
    A[132:ATLAS, :] = 31                          # rows 0-131 原样恢复, 其余清底

    zp = ImageFont.truetype(a.ttf, a.size)
    sh = ImageFont.truetype(a.ttf_fallback, a.size) if getattr(a, 'ttf_fallback', None) else None

    def render14(ch):
        """→ (strip 14 行 × iw, iw, ytop, ybot) — strip = 画布 rows[3,17), 水平裁墨 bbox"""
        for fnt in (zp, sh) if sh is not None else (zp,):
            img = Image.new('L', (20, 20), 255)
            d = ImageDraw.Draw(img)
            d.text((3, 3), ch, font=fnt, fill=0)
            arr = np.asarray(img)
            ink = arr < 128
            if not ink.any():
                continue
            ys, xs = np.where(ink)
            yt, yb = int(ys.min()) - 3, int(ys.max()) - 3
            iw = int(xs.max() - xs.min() + 1)
            if iw > cw - 2 * margin or not (0 <= yt and yb <= 13):
                continue
            strip = np.where(ink[3:17, xs.min():xs.max() + 1], 0, 31).astype(np.uint8)
            return strip, iw, yt, yb
        die('字 %r 无法渲染 (墨超 %dx%d 预算)' % (ch, cw - 2 * margin, 13))

    def draw_cjk(ch, x, y):
        strip, iw, yt, yb = render14(ch)
        stop = y + 3 - (1 if yb == 13 else 0)
        A[stop + yt:stop + yb + 1, x + margin:x + margin + iw] = strip[yt:yb + 1]
        if not (stop + yt >= y + 2 and stop + yb <= y + chh):
            die('%r 墨出采样域' % ch)
        return iw, yt, yb

    # 1) CJK pair 格 (码位稀疏保留, 与 zh13_font 同槽位)
    pair_cells = {}
    for ch, (l, t) in kept_pairs.items():
        slot = (l - 0xA1) * 94 + (t - 0xA1)
        col, row = slot % ncol, slot // ncol
        x, y = X0 + cw * col, gy + chh * row
        if y + chh >= en_a:
            die('pair slot %d 越入 EN 带' % slot)
        iw, yt, yb = draw_cjk(ch, x, y)
        pair_cells[ch] = (x, y, iw, yt, yb)
    # 2) single 格: row18 尾段 + row19 + 孔位 (孔位 = 683 域内未占用槽)
    kept_slots = {(l - 0xA1) * 94 + (t - 0xA1) for (l, t) in kept_pairs.values()}
    holes = sorted(s for s in range(683) if s not in kept_slots)
    free_cells = [(X0 + cw * c, gy + chh * 18) for c in range(17, ncol)]
    free_cells += [(X0 + cw * c, gy + chh * 19) for c in range(ncol)]
    free_cells += [(X0 + cw * (s % ncol), gy + chh * (s // ncol)) for s in holes]
    if len(free_cells) < len(singles):
        die('single 格预算 %d < %d' % (len(free_cells), len(singles)))
    single_cells = {}
    for ch, (x, y) in zip(sorted(singles, key=lambda k: singles[k]), free_cells):
        iw, yt, yb = draw_cjk(ch, x, y)
        single_cells[ch] = (x, y, iw, yt, yb)
    code2single = {code: ch for ch, code in singles.items()}
    assert len(code2single) == len(singles)
    # 3) default EN 98 码位 Zpix 重绘 (A/B 带, pitch = 墨宽+2)
    en_cells = {}
    x, band = X0, 'A'
    for c in V8_EN_REDRAW:
        strip, iw, yt, yb = render14(V8_EN_SRC.get(c, chr(c)))
        pitch = iw + 2 * margin
        if x + pitch > ATLAS - 1:
            band = 'B' if band == 'A' else None
            if band is None:
                die('EN 带溢出')
            x = X0
        sy = en_a if band == 'A' else en_b
        stop = sy + 2
        A[stop + yt:stop + yb + 1, x + margin:x + margin + iw] = strip[yt:yb + 1]
        if not (stop + yt >= sy and stop + yb <= sy + chh - 2):
            die('EN %02X 墨出采样域' % c)
        en_cells[c] = (x, pitch, band, iw, yt, yb)
        x += pitch
    en_tail_x = x if band == 'B' else None
    if en_tail_x is None:
        die('EN 只用了 A 带?')
    clash = sorted(set(code2single) & set(en_cells))
    if clash:
        die('single 码位与 EN 带冲突: %s' % [hex(c) for c in clash])
    # 4) large 键盘 43 码位 Zpix @ C 带 (26 行, fld[1]=large 原值 → 1:1)
    kbd_cells = {}
    x = X0
    for c in sorted(V8_KBD):
        strip, iw, yt, yb = render14(chr(c))
        pitch = iw + 2 * margin
        if x + pitch > ATLAS - 1:
            die('键盘带溢出 @%02X' % c)
        A[kbd_strip + yt:kbd_strip + yb + 1, x + margin:x + margin + iw] = strip[yt:yb + 1]
        if not (kbd_strip + yt >= kbd_v0 + 2 and kbd_strip + yb <= kbd_v1 - 2):
            die('KBD %02X 墨出采样域' % c)
        kbd_cells[c] = (x, pitch, iw, yt, yb)
        x += pitch
    # 5) FONT.RES
    def space_rec():
        w = 10
        xx = en_tail_x + 1
        return (0, 10, xx - X0, en_b - 2, xx - X0 + w, en_b - 2 + chh)
    srec = space_rec()
    out = bytearray()
    out += struct.pack('<I', 20) + ft[4:24]
    out += struct.pack('<I', 3)
    for fi, nm in ((0, 'large'), (1, 'default'), (2, 'huge')):
        fld = list(F0[fi][1])
        if nm != 'large':
            fld[1] = chh
        if nm == 'huge':
            fld[4], fld[5] = 16, 6
        recs = []
        if nm == 'large':
            for c in range(0x20, 0x100):
                if c in code2single:
                    xx, y, iw, _yt, _yb = single_cells[code2single[c]]
                    recs.append((0, cw, xx - X0, y, xx - X0 + cw, y + chh))
                elif c in kbd_cells:
                    xx, pitch, iw, _yt, _yb = kbd_cells[c]
                    recs.append((0, pitch, xx - X0, kbd_v0, xx - X0 + pitch, kbd_v1))
                else:
                    recs.append(tuple(F0[0][2][c - 0x20]))
        elif nm == 'default':
            for c in range(0x20, 0x100):
                if c in en_cells:
                    xx, pitch, band_, _iw, _yt, _yb = en_cells[c]
                    sy = en_a if band_ == 'A' else en_b
                    recs.append((0, pitch, xx - X0, sy - 2, xx - X0 + pitch, sy - 2 + chh))
                elif c in code2single:
                    xx, y, iw, _yt, _yb = single_cells[code2single[c]]
                    recs.append((0, cw, xx - X0, y, xx - X0 + cw, y + chh))
                else:
                    recs.append(srec)
        else:
            for c in range(0x20, 0x80):
                if c in en_cells:
                    xx, pitch, band_, _iw, _yt, _yb = en_cells[c]
                    sy = en_a if band_ == 'A' else en_b
                    recs.append((0, pitch, xx - X0, sy - 2, xx - X0 + pitch, sy - 2 + chh))
                else:
                    recs.append(srec)
        if len(recs) != fld[4] * fld[5]:
            die('%s 记录数 %d != %d' % (nm, len(recs), fld[4] * fld[5]))
        out += struct.pack('<I', len(nm)) + nm.encode()
        out += struct.pack('<14I', *fld)
        for r in recs:
            out += struct.pack('<BB4H', *r)
    out += struct.pack('<I', ns) + styles
    expanded = bytes(out)
    if len(expanded) > FT_LIMIT:
        die('展开态 %d > %d' % (len(expanded), FT_LIMIT))
    # 6) 自检: rows 0-131 verbatim / 记录逐码位 / 采样域 (CJK+EN+KBD, 采样窗 ±1) / 带间 / 回环
    F2, ns2, st2 = parse_faces(expanded)
    if ns2 != ns or st2 != styles:
        die('样式表回环失败')
    for c, ch in code2single.items():
        xx, y, iw, _yt, _yb = single_cells[ch]
        if tuple(F2[1][2][c - 0x20]) != (0, cw, xx - X0, y, xx - X0 + cw, y + chh):
            die('single 码位 %02X 记录未指向网格格' % c)
        if tuple(F2[0][2][c - 0x20]) != (0, cw, xx - X0, y, xx - X0 + cw, y + chh):
            die('large single 码位 %02X 记录未指向网格格' % c)
    for c, (xx, pitch, _iw, _yt, _yb) in kbd_cells.items():
        if tuple(F2[0][2][c - 0x20]) != (0, pitch, xx - X0, kbd_v0, xx - X0 + pitch, kbd_v1):
            die('large kbd 码位 %02X 记录错' % c)
    for c, (xx, pitch, band_, _iw, _yt, _yb) in en_cells.items():
        sy = en_a if band_ == 'A' else en_b
        r = (0, pitch, xx - X0, sy - 2, xx - X0 + pitch, sy - 2 + chh)
        if tuple(F2[1][2][c - 0x20]) != r:
            die('EN 码位 %02X default 记录错' % c)
        if c < 0x80 and tuple(F2[2][2][c - 0x20]) != r:
            die('EN 码位 %02X huge 记录错' % c)
    if not (A[0:132] == ORIG[0:132]).all():
        die('rows 0-131 被改写')
    inkm = A != 31
    for lo, hi in ((130, 133), (en_a - 2, en_a), (467, 470), (483, 488), (509, 512)):
        if inkm[lo:hi, :].any():
            die('带间空白 %d-%d 被侵' % (lo, hi))
    cells_all = []
    for kind, dct, w_, sy_off in (('pair', pair_cells, cw, 2), ('single', single_cells, cw, 2)):
        for ch, (x, y, iw, yt, yb) in dct.items():
            stop = y + 3 - (1 if yb == 13 else 0)
            cells_all.append((x, y + sy_off, w_, y + sy_off + chh,
                              x + margin, stop + yt, x + margin + iw, stop + yb + 1, kind, ch))
    for c, (x, pitch, band_, iw, yt, yb) in en_cells.items():
        sy = en_a if band_ == 'A' else en_b
        cells_all.append((x, sy, pitch, sy + chh, x + margin, sy + 2 + yt,
                          x + margin + iw, sy + 2 + yb + 1, 'en', chr(c)))
    for c, (x, pitch, iw, yt, yb) in kbd_cells.items():
        cells_all.append((x, kbd_v0 + 2, pitch, kbd_v1 + 2, x + margin, kbd_strip + yt,
                          x + margin + iw, kbd_strip + yb + 1, 'kbd', chr(c)))
    bad_cells = []
    for x, ry0, pw, ry1, ix0, iy0, ix1, iy1, kind, ch in cells_all:
        dom = inkm[ry0 - 1:ry1 + 1, x - 1:x + pw + 1]
        mask = np.ones(dom.shape, dtype=bool)
        mask[iy0 - (ry0 - 1):iy1 - (ry0 - 1), ix0 - (x - 1):ix1 - (x - 1)] = False
        if int(dom[mask].sum()):
            bad_cells.append((kind, ch))
    if bad_cells:
        die('采样域渗墨格 %d: %s' % (len(bad_cells), bad_cells[:8]))
    payload = dp_compress(expanded, verbose=False)
    if len(payload) > PAYLOAD_MAX:
        die('payload %d > %d' % (len(payload), PAYLOAD_MAX))
    frame = struct.pack('<II', len(payload), len(expanded)) + payload
    slot = frame + b'\x00' * (SLOT_STORED - len(frame))
    back, _st = decode_entry(slot)
    if back != expanded:
        die('槽回环失败')
    pak0[SURF:SURF + ATLAS * ATLAS] = A.tobytes()
    lines = ['# v8 layout CH=%d grid=(%d cols) pitch=%dx%d y0=%d margin=%d en=(%d,%d) kbd=(%d,%d) dv=2'
             % (chh, ncol, cw, chh, gy, margin, en_a, en_b, kbd_v0, kbd_v1)]
    for ch in kept_pairs:
        x, y, iw, yt, yb = pair_cells[ch]
        lines.append('pair %s cell=(%d,%d) ink=%dx%d rec=(%d,%d,%d,%d) adv=%d'
                     % (ch, x, y, iw, yb - yt + 1, x - X0, y, x - X0 + cw, y + chh, cw))
    for ch in single_cells:
        x, y, iw, yt, yb = single_cells[ch]
        lines.append('single %s code=0x%02X cell=(%d,%d) ink=%dx%d rec=(%d,%d,%d,%d) adv=%d'
                     % (ch, singles[ch], x, y, iw, yb - yt + 1, x - X0, y, x - X0 + cw, y + chh, cw))
    for c in sorted(en_cells):
        xx, pitch, band_, iw, yt, yb = en_cells[c]
        sy = en_a if band_ == 'A' else en_b
        lines.append('EN %02X band=%s rec=(%d,%d,%d,%d) adv=%d ink=%dx%d'
                     % (c, band_, xx - X0, sy - 2, xx - X0 + pitch, sy - 2 + chh, pitch, iw, yb - yt + 1))
    for c in sorted(kbd_cells):
        xx, pitch, iw, yt, yb = kbd_cells[c]
        lines.append('KBD %02X rec=(%d,%d,%d,%d) adv=%d ink=%dx%d'
                     % (c, xx - X0, kbd_v0, xx - X0 + pitch, kbd_v1, pitch, iw, yb - yt + 1))
    return dict(pak=bytes(pak0), expanded=expanded, slot=slot, codes=singles,
                pair_of={k: list(v) for k, v in kept_pairs.items()},
                markers=[], chosen=[], pairs=[], cleared=[], layout_extra=[],
                layout_lines=lines,
                grid=dict(ncol=ncol, cw=cw, ch=chh, gridy=gy, margin=margin,
                          x0=X0, en_y=[en_a, en_b], kbd_band=[kbd_v0, kbd_v1], dv=2))


def build_single(a):
    """ZH3/ZH5 保守路线: 记录矩形不动, 仅重绘既有格像素。"""
    ft = open(a.base_ft, 'rb').read()
    faces, ns, styles = parse_faces(ft)
    def_f = [f for f in faces if f[0] == 'default'][0]
    singles, _pairs, markers = load_charset(a.charset, 'single')
    if markers:
        die('single 模式不支持 marker 字符')
    singles2, _free = alloc_single_codes(singles, 0)
    codes = dict(singles2)
    pak = bytearray(open(a.base_pak, 'rb').read())
    base_pak = bytes(pak)
    A = np.frombuffer(bytes(pak[SURF:SURF + ATLAS * ATLAS]),
                      dtype=np.uint8).reshape(ATLAS, ATLAS).copy()
    f = ImageFont.truetype(a.ttf, a.size)
    rects = []
    for ch, code in singles2:
        if code < 0x20 or code > 0xFE:
            die('码位 0x%02X 越界 (%r)' % (code, ch))
        rec = def_f[2][code - 0x20]
        x0, y0, x1, y1 = rect_of(rec)
        w, h = x1 - x0, y1 - y0
        m = f.getmask(ch, mode='L')
        gw, gh = m.size
        if gh > h or gw > w:
            die('%r 字形 %dx%d 超出 0x%02X 格 %dx%d — 请减字号或换格'
                % (ch, gw, gh, code, w, h))
        ga = np.asarray(m, dtype=np.uint8).reshape(gh, gw)
        tx = np.where(ga > 128, 0, 31).astype(np.uint8)
        oy, ox = y0 + (h - gh) // 2, x0 + (w - gw) // 2
        A[oy:oy + gh, ox:ox + gw] = tx
        rects.append((ch, code, (x0, y0, x1, y1)))
    pak[SURF:SURF + ATLAS * ATLAS] = A.tobytes()
    diff = [i for i in range(len(base_pak)) if base_pak[i] != pak[i]]
    white = np.zeros(ATLAS * ATLAS, dtype=bool)
    for _ch, _c, (x0, y0, x1, y1) in rects:
        white[y0:y1, x0:x1] = True
    outside = [i - SURF for i in diff if not (SURF <= i < SURF + ATLAS * ATLAS
                                              and white[i - SURF])]
    if outside:
        die('PAK 差异越出重绘矩形: %d 处' % len(outside))
    return dict(pak=bytes(pak), expanded=None, slot=None,
                codes=codes, pair_of={}, markers=[],
                chosen=[(r[2][1], r[2][0]) for r in rects],
                pairs=[], cleared=[], layout_extra=[(r[1], r[0], 'single', '原格重绘')
                                                    for r in rects])


def main():
    ap = argparse.ArgumentParser(description='GR PS2 字库生成器 (FONT.RES + COMMON.PAK)')
    ap.add_argument('--charset', required=True, help='字符表 CSV (char,strategy[,code])')
    ap.add_argument('--base-ft', required=True, help='FONT.RES 展开态基座 (7222B)')
    ap.add_argument('--base-pak', required=True, help='COMMON.PAK 基座 (400659B)')
    ap.add_argument('--ttf', required=True, help='TTF 字体 (如 SimHei)')
    ap.add_argument('--size', type=int, default=16, help='字形像素 (默认 16)')
    ap.add_argument('--mode', choices=('dbcs', 'single', 'v6', 'v7', 'v8', 'v9'), default='dbcs')
    ap.add_argument('--grid-cols', type=int, default=37, help='v6: 网格列数 (默认 37 = 边缘留白铁律)')
    ap.add_argument('--cell-w', type=int, default=13, help='v6: 水平 pitch (默认 13 = 墨+2×margin)')
    ap.add_argument('--cell-h', type=int, default=15)
    ap.add_argument('--grid-y', type=int, default=128, help='v6: 网格起始行 (禁写区 rows 0-127)')
    ap.add_argument('--en-y', type=int, default=445, help='v6: EN 区首行 (行 2 = en_y+CH+1)')
    ap.add_argument('--ch', type=int, default=15)
    ap.add_argument('--margin', type=int, default=1, help='v6: 格内字形内缩 (默认 1px)')
    ap.add_argument('--ttf-fallback', default=None, help='v6: 回退 TTF (墨超预算时, 可选)')
    ap.add_argument('--en-band-a', type=int, default=473, help='v7: EN S 带行 A (记录 v0=S-2)')
    ap.add_argument('--en-band-b', type=int, default=492, help='v7: EN S 带行 B')
    ap.add_argument('--kbd-v0', type=int, default=482, help='v8: large 键盘带起 (26 行带)')
    ap.add_argument('--kbd-v1', type=int, default=508, help='v8: large 键盘带止')
    ap.add_argument('--trim', default=None, help='v7: 裁字表 json {"trim19": [...]} (孔位格来源)')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--zh16-script', default=None,
                    help='v9: 完全扩容(ZH16 1212 字 CH13 反转布局)规范实现脚本路径 '
                         '(main 已无此会话脚本, 在 archive/GR_ZH36+ 分支 work/zh16/zh16_font.py)')
    a = ap.parse_args()

    if a.mode == 'v9':
        # ---- v9: 完全扩容 (ZH16) —— 规范实现委托 ----
        # 配方: 512x512 CH13 反转布局 (Y0=2, NCOL=37, CW=13, CH=13, skip r>=14:+39,
        #       EN A S=476 / B S=491 13 行带), 1212 字 = 690 冻结 pair + 446 新 pair
        #       (slot 707..1152) + 76 single; fld large/default=13, huge=16。
        # 详见 FONT_CAPACITY.md 十五 与 zh16_font.py (字节级规范实现)。
        if not a.zh16_script or not os.path.exists(a.zh16_script):
            raise SystemExit('[font_build] --mode v9 需 --zh16-script 指向 zh16_font.py '
                             '(main 不入库; 可从 archive/GR_ZH36 等分支取 work/zh16/zh16_font.py)')
        import runpy
        print('[font_build] mode=v9 (完全扩容 ZH16) — 委托规范实现: %s' % a.zh16_script)
        runpy.run_path(a.zh16_script, run_name='__main__')
        print('[font_build] mode=v9 PASS — 产物见脚本自身输出目录')
        return

    os.makedirs(a.out_dir, exist_ok=True)
    res = build_dbcs(a) if a.mode == 'dbcs' else (
        build_v6(a) if a.mode == 'v6' else (
        build_v7(a) if a.mode == 'v7' else (
        build_v8(a) if a.mode == 'v8' else build_single(a))))

    open(os.path.join(a.out_dir, 'COMMON_PAK_NEW.bin'), 'wb').write(res['pak'])
    with open(os.path.join(a.out_dir, 'charset_compiled.json'), 'w',
              encoding='utf-8') as f:
        json.dump({'mode': a.mode,
                   'codes': res['codes'],
                   'pair_of': {k: list(v) for k, v in res['pair_of'].items()},
                   'markers': res['markers'],
                   'protected': ['0x%02X' % c for c in PROTECTED],
                   'mark_codes': ['0x%02X' % c for c in MARK_CODES],
                   'grid': res.get('grid')},
                  f, ensure_ascii=False, indent=1)
    if res['expanded'] is not None:
        open(os.path.join(a.out_dir, 'FONT_RES_expanded.bin'), 'wb').write(res['expanded'])
        open(os.path.join(a.out_dir, 'FONT_RES_slot.bin'), 'wb').write(res['slot'])
    with open(os.path.join(a.out_dir, 'layout.txt'), 'w', encoding='utf-8') as f:
        f.write('# font_build layout — mode=%s size=%d ttf=%s\n' % (a.mode, a.size, a.ttf))
        for k, (y0, x) in enumerate(res['chosen']):
            ch = res['pairs'][k] if k < len(res['pairs']) else '?'
            f.write('idx=%d cell=(%d,%d) %s rec=(%d,%d,%d,%d,%d)\n'
                    % (224 + k, x, y0, ch, x - 20, y0, x - 20 + CELL_W,
                       y0 + CELL_H, ADV16))
        for idx, ch, pair, note in res['layout_extra']:
            f.write('idx=%d %s %s %s\n' % (idx, ch, pair, note))
        f.write('# 收割清底矩形: %d\n' % len(res['cleared']))
    n_pair = len(res['pairs'])
    print('[font_build] mode=%s single=%d pair=%d marker=%d'
          % (a.mode, len(res['codes']), n_pair, len(res['markers'])))
    if res['expanded'] is not None:
        payload_len = struct.unpack_from('<I', res['slot'], 0)[0]
        print('[font_build] FONT.RES 展开 %dB ≤ %d, DP payload %dB ≤ %d, 槽回环 PASS'
              % (len(res['expanded']), FT_LIMIT, payload_len, PAYLOAD_MAX))
    print('[font_build] PAK 差异白名单自检 PASS — 输出 %s' % a.out_dir)
    print('[font_build] PASS')


if __name__ == '__main__':
    main()
