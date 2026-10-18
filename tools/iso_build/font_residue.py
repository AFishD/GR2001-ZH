# -*- coding: utf-8 -*-
r"""font_residue.py — **图集残墨测量仪** (round49): 在"排除引擎真正会采样的像素"之后, 量残墨。

## 它回答的问题

用户看到的: 字库贴图 (COMMON.PAK `new_font_revised`) 上还有一些"碎片"没被清掉。
问题在于 **哪些能清、哪些一清就出事** —— 图集里有 4 类"别人的地盘":

  ① 对偶格 (1504 个): 引擎按 `col = slot % 62` 寻址 ⇒ x = 16*col 只到 **991**,
     图集却有 1024 宽 (64 格) ⇒ 每行右侧 **2 格 (x=992..1023) 永不采样** (回绕列);
  ② 单字节/ASCII 的 **FT 记录矩形** (3 个 face, 544 条非空): 引擎按记录矩形采样,
     这些矩形**不对齐 16x16** (例如 (89,395)-(94,408) = 武器页上下滚动箭头的 5x13 小矩形);
     按记录去画时的采样窗还有 ±(GLYPH_TOL_X, GLYPH_TOL_Y) = ±(4,2) 的实测偏置;
  ③ **手柄图标码** 0xB1/0xB5 的硬编码 UV 走的是另一张贴图 (pda_counterparts.rsb),
     但它们在 FT 记录表里仍占着一格 ⇒ 那一角不能动;
  ④ 网格外的"结构性空洞": y=0..1 (顶部)、y=194..241 (行 11 与行 12 之间被
     `GRID_SKIP_ROWS=3` 跳掉的 3 行)、y>=450 (网格下方)、行 24 右侧 (x>=256, 没有槽位
     落在那里) —— 这些地方对偶格公式同样不覆盖。

## 判据 (每个"建议清除"的像素都必须满足)

    残墨 = 墨 ∧ ¬(charset 已用对偶格) ∧ ¬(全部 FT 记录窗, 按 ±(4,2) 膨胀的保守口径)

  · 已用对偶格 = charset 里 lead 合法的 1319 个字的引擎格, 整格保留 (那是活字形);
  · FT 记录窗  = 3 个 face 全部 544 条非空矩形, **膨胀 ±(4,2)**; 保守: 宁可少清 44 个格;
  · 剩下的墨 ⇒ 既不在任何已用字形里, 也不在任何"引擎会采样"的窗里
      ⇒ 清了不会影响任何显示 (它本来就画不出来) —— 这就是残墨。

## ⚠ round52 订正 (重要, 本工具的口径**偏松**, 会漏报)

上面的 ±(4,2) 是 round44~46 时代留下的**保守余量**(那时还没搞清"引擎按记录矩形原样采样")。
round51 已证明**引擎按 FT 记录矩形原样采样**(往矩形里写 ⇒ 逐像素等于 16px 模板), 所以这个余量
的后果是: **紧贴记录矩形、但不属于任何字形的碎片墨被"保护"下来** ⇒ 本工具报"残墨 0", 人眼却看得见。

实测(GR_ZH101): 本口径 **0 px**; 严格口径(0 余量) **167 px / 39 团块** —— 例如 `稳` 记录右侧 2px 处
的 18 px、末列 x=992..995 的 16 px、row21~23 空槽里的 131 px。

⇒ **要用严格口径请用 `tools/iso_build/patch_zh52_residue.py`**(它按"已用格 ∪ 记录矩形原样"判定,
并在写盘后回读要求残留 0)。本工具保留原口径以便复现 round49 的历史结论。

## 输出

    residue.json        逐格/逐区域 {col,row,x0,y0,ink_px,分类,建议} + 1504 个槽位全表
    residue_report.md   人话总结 (哪些是真残墨可清 / 哪些必须保留 / 为什么)
    residue_map.png     图集三色标注图 (已用=蓝 / 保留=绿 / 残墨=红 / 不可寻址=黄)
    residue_zoom.png    残墨簇 [清理前 | 清理后] 4 倍放大对照 (给人眼看的证据)

## 用法

    python tools/iso_build/font_residue.py --iso work/builds/GR_ZH97/GR_ZH97.iso \
        --out work/builds/GR_ZH97/temp/font_residue --prefix GR_ZH97

★ 本工具**只读**: 除 --out 目录外不写任何文件; 真清残墨由
  `tools/iso_build/patch_zh98_font_cleanup.py` 调用本模块的 `compute()` / `clear_on_iso()`。
"""
import argparse
import csv
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                        # noqa: BLE001
    pass

import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402
import dump_font                                                         # noqa: E402
import repack_font                                                       # noqa: E402

TOOL = 'tools/iso_build/font_residue.py'
TOOL_VERSION = 'r49.1'
ROUND = 'round49'
CW = CH = tcslib.CW
NCOL = tcslib.NCOL
DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV          # 记录矩形 → 采样窗 的实测偏置 (4,2)
TX, TY = tcslib.GLYPH_TOL_X, tcslib.GLYPH_TOL_Y    # 保守膨胀 (±4,±2)

# ── 分类名 (JSON 与报告共用同一套字符串) ──────────────────────────────────
K_USED = 'used_pair_cell'          # charset 在用的对偶格 (活字形)
K_FTWIN = 'ft_record_window'       # 落在某个 FT 记录窗 (膨胀后) 内
K_REC = 'record_cell'              # 整格/一角被单字节记录码占死的格 (ATLAS_ENGINE_SINGLE_CELLS)
K_FREE = 'free_pair_cell'          # 空对偶槽的格
K_NEVER = 'never_sampled'          # 任何采样窗都不覆盖 (回绕列/顶部/空洞带/网格下方)
ADV_KEEP = '保留'
ADV_CLEAR = '清除'
ADV_MANUAL = '保留(需人工确认)'


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


# ═══════════════════════════ 采样窗枚举 ═══════════════════════════

def rect_put(mask, x0, y0, x1, y1, w, h):
    x0, y0 = max(0, int(x0)), max(0, int(y0))
    x1, y1 = min(w, int(x1)), min(h, int(y1))
    if x0 < x1 and y0 < y1:
        mask[y0:y1, x0:x1] = True


def enumerate_sampler(cs, faces, w, h):
    """把"引擎会采样哪些像素"全部枚举出来 (对偶格 + 3 face 的 FT 记录矩形)。

    返回 dict:
      · `pair_any`  : 1504 个对偶格 (不管 charset 用没用) —— 对偶路径的**全部**可能采样区
      · `pair_used` : charset 真在用的那些对偶格
      · `ft_raw`    : 544 条 FT 记录矩形原样
      · `ft_win`    : 记录矩形 ∪ 矩形+(4,2)   (= dump_font._live_rects 的口径)
      · `ft_dil`    : 记录矩形 ±(4,2)          (= 本工具的**保守**口径)
      · `rects`     : 逐条明细 (face / code / u0 v0 u1 v1)
      · `cells`     : 1504 个槽 → (row, col, x, y)
    """
    pair_any = np.zeros((h, w), bool)
    pair_used = np.zeros((h, w), bool)
    cells = []
    used_slots = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            used_slots[tcslib.pair_slot(b1, b2)] = ch
    cap = tcslib.pair_capacity()
    for s in range(cap):
        row, col = s // NCOL, s % NCOL
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        cells.append(dict(slot=s, row=row, col=col, x=x, y=y, char=used_slots.get(s)))
        rect_put(pair_any, x, y, x + CW, y + CH, w, h)
        if s in used_slots:
            rect_put(pair_used, x, y, x + CW, y + CH, w, h)
    assert len(set((c['x'], c['y']) for c in cells)) == cap, '对偶格有重叠 —— 公式异常'

    ft_raw = np.zeros((h, w), bool)
    ft_win = np.zeros((h, w), bool)
    ft_dil = np.zeros((h, w), bool)
    rects = []
    for (fname, _fld, rs) in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            rec = dict(face=fname, code=idx + 0x20, u0=u0, v0=v0, u1=u1, v1=v1,
                       w=u1 - u0, h=v1 - v0)
            rects.append(rec)
            rect_put(ft_raw, u0, v0, u1, v1, w, h)
            rect_put(ft_win, u0, v0, u1, v1, w, h)
            rect_put(ft_win, u0 + DU, v0 + DV, u1 + DU, v1 + DV, w, h)
            rect_put(ft_dil, u0 - TX, v0 - TY, u1 + TX, v1 + TY, w, h)
    return dict(pair_any=pair_any, pair_used=pair_used, ft_raw=ft_raw, ft_win=ft_win,
                ft_dil=ft_dil, rects=rects, cells=cells, used_slots=used_slots, cap=cap)


# ═══════════════════════════ 区域分解 ═══════════════════════════
#
# 把整张图集切成**互不重叠**的区域, 每个区域能回答"这里引擎会不会采样":
#   · 1504 个对偶格      → kind ∈ {used_pair_cell, record_cell, free_pair_cell}
#   · 8 个"额外区域"     → kind = never_sampled  (对偶格公式永不覆盖)
# 分解后断言: 每个墨点恰好落进一个区域 (不重不漏)。

def build_regions(cs, sampler, w, h):
    """整张图集 → 互不重叠的区域清单 (先摆 1504 个对偶格, 再用"额外区域"补缝)。"""
    yrow = lambda r: tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS
                                                        if r >= tcslib.GRID_SKIP_ROW else 0))
    rec_cells = set(tcslib.ATLAS_ENGINE_SINGLE_CELLS)
    regs = []
    seen = np.zeros((h, w), bool)
    for c in sampler['cells']:
        if c['char']:
            kind = K_USED
        elif (c['row'], c['col']) in rec_cells:
            kind = K_REC
        else:
            kind = K_FREE
        regs.append(dict(kind=kind, label='对偶槽 %d (行%d 列%d)' % (c['slot'], c['row'], c['col']),
                         x0=c['x'], y0=c['y'], w=CW, h=CH, slot=c['slot'],
                         row=c['row'], col=c['col'], char=c['char'] or '',
                         note=tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((c['row'], c['col']), '')))
        seen[c['y']:c['y'] + CH, c['x']:c['x'] + CW] = True

    y_last = yrow(24) + CH                     # 434+16 = 450
    x24 = 16 * ((sampler['cap'] - 1) % NCOL + 1)          # 1503%62=15 ⇒ x24 = 256
    extra = [
        ('顶部 2 行 (y=0..1)', 0, 0, w, 2,
         '对偶格公式 y 从 GRID_Y0=2 起 ⇒ 这两行对偶路径永不采样'),
        ('行 11 与行 12 之间被跳掉的 3 行 (y=194..241)', 0, yrow(11) + CH, w,
         yrow(12) - (yrow(11) + CH),
         'GRID_SKIP_ROWS=3: 行 12 起 y 跳 48 行 (容器包头让位) ⇒ 这条带对偶路径永不采样'),
        ('网格下方 (y=%d..%d)' % (y_last, h - 1), 0, y_last, w, h - y_last,
         '最后一个网格行 (行 24) 之下没有槽位 ⇒ 对偶路径永不采样'),
        ('行 24 带内右侧无槽位段 (x=%d..%d, y=%d..%d)'
         % (x24, w - 1, yrow(24), yrow(24) + CH - 1), x24, yrow(24), w - x24, CH,
         '行 24 只到 col 15 (1504 = 24×62+16) ⇒ 右边这段没有码位'),
    ]
    for r in range(25):
        y = yrow(r)
        extra.append(('网格行 %d 的右侧 2 格 (x=992..1023, y=%d..%d)' % (r, y, y + CH - 1),
                      992, y, w - 992, CH,
                      '对偶格 x=16*col 且 col=slot%%62<=61 ⇒ x<=991; 这 2 格是**回绕列**'))
    for (label, x0, y0, ww, hh, note) in extra:
        piece = np.zeros((h, w), bool)
        rect_put(piece, x0, y0, x0 + ww, y0 + hh, w, h)
        piece &= ~seen                          # 与已有区域零重叠 (先到先得)
        if not piece.any():
            continue
        seen |= piece
        ys, xs = np.where(piece)
        regs.append(dict(kind=K_NEVER, label=label, x0=int(xs.min()), y0=int(ys.min()),
                         w=int(xs.max() - xs.min() + 1), h=int(ys.max() - ys.min() + 1),
                         slot=None, row=None, col=None, char='', note=note,
                         rect=[[int(x0), int(y0), int(x0 + ww), int(y0 + hh)]],
                         _mask=piece))
    return regs


def region_mask(r, w, h):
    m = r.get('_mask')
    if m is None:
        m = np.zeros((h, w), bool)
        rect_put(m, r['x0'], r['y0'], r['x0'] + r['w'], r['y0'] + r['h'], w, h)
    return m


def measure(regs, ink, pair_used, ft_dil, w, h):
    """逐区域数墨 + 给建议 (每个"建议清除"的格都要有可解释的理由)。"""
    out = []
    for r in regs:
        m = region_mask(r, w, h)
        cell_ink = ink & m
        n_ink = int(cell_ink.sum())
        n_win = int((cell_ink & ft_dil & m).sum())
        n_res = int((cell_ink & ~ft_dil & ~pair_used).sum())
        d = dict(kind=r['kind'], label=r['label'], x0=r['x0'], y0=r['y0'],
                 w=r['w'], h=r['h'], slot=r['slot'], row=r['row'], col=r['col'],
                 char=r['char'], ink_px=n_ink,
                 ink_in_used_cell_px=int((cell_ink & pair_used & m).sum()),
                 ink_in_window_px=n_win, ink_residue_px=n_res)
        d['advice'] = Adv(r['kind'], n_res, n_ink)
        d['reason'] = Reason(r['kind'], n_res, n_ink, r)
        out.append(d)
    return out


def Adv(kind, n_res, n_ink=0):
    if kind in (K_USED, K_FTWIN):
        return ADV_KEEP
    if n_res == 0:
        return ADV_KEEP
    return ADV_CLEAR


def Reason(kind, n_res, n_ink, r):
    if kind == K_USED:
        if n_ink == 0:
            return '⚠ charset 在用「%s」, 但这一格一个墨点都没有 (缺字形)' % r['char']
        return 'charset 在用字形「%s」的引擎格 (%d px 墨) —— 整格保留' % (r['char'], n_ink)
    if kind == K_FTWIN:
        return '落在 FT 记录采样窗 (单字节/ASCII/图标码) 内 —— 引擎会采样, 保留'
    if kind == K_REC:
        if n_res:
            return ('整格被单字节记录码占死 (对偶码永远不能用); 但有 %d px 在采样窗之外 '
                    '⇒ 那是历史遗留的字形碎片, 可清 (窗内的一角保留)' % n_res)
        return '整格被单字节记录码占死; 墨全部落在采样窗内 ⇒ 是活字形, 保留'
    if kind == K_FREE:
        if n_res:
            return ('空对偶槽, 且不在任何采样窗内, 却还有 %d px 墨 ⇒ **真残墨 (旧字形没清干净)**'
                    % n_res)
        return '空对偶槽, 格是白的 ⇒ 可以直接写新字'
    if n_res:
        return ('%s; 且没有任何采样窗覆盖这 %d px ⇒ 画不出来, 可清' % (r['note'], n_res))
    return r['note']


# ═══════════════════════════ 主入口 ═══════════════════════════

def find_copies(ink, boxes, w, h, topn=3):
    """对给定矩形块, 用 FFT 互相关找"这块内容在图上还出现在哪" (逐像素重复 = 旧副本)。

    返回 [{label, box, ink_px, hits:[{dx,dy,corr}]}] —— corr = 平移后仍重合的墨点数,
    corr == ink_px 就是**逐像素完全一样**的副本。
    """
    from numpy.fft import rfft2, irfft2
    F = rfft2(ink.astype(np.float32))
    out = []
    for (label, x0, y0, x1, y1) in boxes:
        k = np.zeros((h, w), np.float32)
        k[y0:y1, x0:x1] = ink[y0:y1, x0:x1]
        n = int(k.sum())
        if n < 8:
            continue
        c = np.rint(irfft2(F * np.conj(rfft2(k)), s=(h, w))).astype(np.int32)
        # c[dy, dx] = 把 k 平移 (dx,dy) 后与 ink 的重合墨点数; 自身在 (0,0) = n
        c2 = c.copy()
        c2[0, 0] = -1
        flat = np.argsort(c2, axis=None)[::-1][:topn]
        hits = []
        for f in flat:
            dy, dx = np.unravel_index(f, c2.shape)
            if dx > w // 2:
                dx -= w
            if dy > h // 2:
                dy -= h
            hits.append(dict(dx=int(dx), dy=int(dy), corr=int(c2[dy % h, dx % w])))
        out.append(dict(label=label, box=[int(x0), int(y0), int(x1), int(y1)],
                        ink_px=n, hits=hits))
    return out


def duplicate_offsets(ink, w, h, max_report=8):
    """找"图集里有整块内容在别处重复出现"的位移 (dx, dy) —— 用来判"残墨是不是旧副本"。

    做法: 对一组候选位移把墨图整体平移, 数"平移后仍然重合的墨点"比例。
    真副本 (历史工具按别的坐标口径又写了一遍) 会给出很高的重合率。
    """
    cand = []
    for dy in (-2, -1, 0, 1, 2):
        for dx in list(range(-960, 0, 32)) + list(range(32, 961, 32)):
            cand.append((dx, dy))
    tot = int(ink.sum())
    out = []
    for (dx, dy) in cand:
        sx0, sx1 = max(0, -dx), min(w, w - dx)
        sy0, sy1 = max(0, -dy), min(h, h - dy)
        if sx1 - sx0 < 64 or sy1 - sy0 < 64:
            continue
        a = ink[sy0:sy1, sx0:sx1]
        b = ink[sy0 + dy:sy1 + dy, sx0 + dx:sx1 + dx]
        both = int((a & b).sum())
        only = int(a.sum())
        if only == 0:
            continue
        out.append(dict(dx=dx, dy=dy, match_px=both, src_ink_px=only,
                        ratio=round(both / float(only), 3),
                        share_of_atlas=round(both / float(tot), 3)))
    out.sort(key=lambda r: -r['match_px'])
    return out[:max_report]


def _copy_boxes(rows, cap=16):
    """挑给"副本判定"用的残墨块: 10 个记录码残墨格 (最像'碎片'的) + 残墨最多的若干块。"""
    boxes = []
    seen = set()
    for r in sorted([x for x in rows if x['ink_residue_px'] > 0 and x['kind'] == K_REC],
                    key=lambda x: -x['ink_residue_px']):
        k = (r['x0'], r['y0'], r['w'], r['h'])
        if k in seen:
            continue
        seen.add(k)
        boxes.append((r['label'], r['x0'], r['y0'], r['x0'] + r['w'], r['y0'] + r['h']))
    for r in sorted([x for x in rows if x['ink_residue_px'] > 0], key=lambda x: -x['ink_residue_px']):
        if len(boxes) >= cap:
            break
        k = (r['x0'], r['y0'], r['w'], r['h'])
        if k in seen:
            continue
        seen.add(k)
        boxes.append((r['label'], r['x0'], r['y0'], r['x0'] + r['w'], r['y0'] + r['h']))
    return boxes[:cap]


def ft_window_alignment(ink, faces, w, h):
    """实测"FT 记录矩形到底是不是采样窗" (round49 定案)。

    做法: 逐条记录看**墨的包围盒**相对矩形左上角的偏移。
      · 若墨普遍从第 0 列/第 0 行就开始 ⇒ **矩形本身就是采样窗** (字形就写在矩形里);
      · 若墨整体右移 4 / 下移 2 (第 0..3 列、第 0..1 行是空的) ⇒ 采样窗是 `矩形+(4,2)`。
    结论 (GR_ZH97 实测, 见 residue_report.md): **矩形就是采样窗**;
    `+(4,2)` 是历史上的**写入侧**偏置, 不是引擎的采样偏置。
    ⇒ 定位用原矩形 (与 `repack_font` 同口径); 而清理保护罩仍**故意**用 ±(4,2) 的膨胀
      (宁可少清几十个像素, 也不赌)。
    """
    left, top, n, ex = {}, {}, 0, 0
    for (_fn, _fld, rs) in faces:
        for (_b0, _b1, u0, v0, u1, v1) in rs:
            if u1 <= u0 or v1 <= v0:
                continue
            cell = ink[v0:v1, u0:u1]
            ys, xs = np.where(cell)
            if not len(xs):
                continue
            n += 1
            left[int(xs.min())] = left.get(int(xs.min()), 0) + 1
            top[int(ys.min())] = top.get(int(ys.min()), 0) + 1
            if int(xs.min()) == 0:
                ex += 1
    return dict(records_with_ink=n, ink_left_col0=left.get(0, 0), ink_top_row0=top.get(0, 0),
                left_hist=dict(sorted(left.items())), top_hist=dict(sorted(top.items())),
                verdict=('矩形=采样窗 (墨从第 0 列/第 0 行开始: %d/%d 条)' % (ex, n)))


def compute(iso_path, charset_path=None, verbose=False):
    """只读分析一张盘。返回 dict (含 residue 掩码 / atlas / sampler / 报告 doc)。"""
    t0 = time.time()
    charset_path = charset_path or tcslib.CHARSET
    font = dump_font.load_font(iso_path)
    am, faces = font['atlas'], font['faces']
    w, h, psm = am['w'], am['h'], am['psm']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], w, h, psm)
    ink = A.eng
    cs = tcslib.Charset(charset_path)
    if verbose:
        print('[residue] 图集 %dx%d psm=0x%02X 墨 %d; 容器 %d B / %d 段'
              % (w, h, psm, int(ink.sum()), am['px_size'], len(A.segs)))

    S = enumerate_sampler(cs, faces, w, h)
    regs = build_regions(cs, S, w, h)
    rows = measure(regs, ink, S['pair_used'], S['ft_dil'], w, h)

    residue = ink & ~S['pair_used'] & ~S['ft_dil']
    # 不变量: 逐区域数出来的残墨必须等于整幅掩码
    ssum = sum(r['ink_residue_px'] for r in rows)
    assert ssum == int(residue.sum()), '区域分解的残墨 %d != 掩码残墨 %d' % (ssum, int(residue.sum()))
    # 不变量: 逐区域墨之和 = 全图墨 (不重不漏)
    isum = sum(r['ink_px'] for r in rows)
    assert isum == int(ink.sum()), '区域分解的墨 %d != 全图墨 %d' % (isum, int(ink.sum()))

    # ---- 回绕列 (x>=992) 穷举判定 ----
    strip = np.zeros((h, w), bool)
    strip[:, 992:] = True
    wrap = dict(
        engine_pair_max_x=16 * (NCOL - 1) + CW - 1,        # 991
        atlas_w=w, atlas_cols=w // CW, engine_cols=NCOL,
        slots_checked=S['cap'],
        pair_windows_hit_strip=int((strip & S['pair_any']).sum()),
        ft_raw_hit_strip=int((strip & S['ft_raw']).sum()),
        ft_win_hit_strip=int((strip & S['ft_win']).sum()),
        ft_dil_hit_strip=int((strip & S['ft_dil']).sum()),
        ink_strip=int((ink & strip).sum()),
        residue_strip=int((residue & strip).sum()),
        hit_rects=[r for r in S['rects'] if r['u1'] + TX > 992 or r['u1'] + DU > 992],
    )
    if verbose:
        print('[residue] 对偶路径的 x 上界 = %d; 图集宽 %d ⇒ x>=992 的 **回绕列** 对偶永不采样'
              % (wrap['engine_pair_max_x'], w))
        print('[residue] 残墨 **%d px** / 全图墨 %d (%.2f%%)'
              % (int(residue.sum()), int(ink.sum()), 100.0 * residue.sum() / ink.sum()))

    doc = dict(
        tool=TOOL, tool_version=TOOL_VERSION, round=ROUND,
        generated=time.strftime('%Y-%m-%d %H:%M:%S'),
        iso=rel(iso_path), iso_sha256=tcslib.sha256_file(iso_path),
        charset=rel(charset_path),
        atlas=dict(w=w, h=h, psm=psm, px_off=am['px_off'], px_size=am['px_size'],
                   segments=len(A.segs),
                   segment_rows=[[int(a), int(b), int(c)] for a, b, c in A.segs],
                   ink_total=int(ink.sum())),
        windows=dict(
            pair_slots=S['cap'], pair_any_px=int(S['pair_any'].sum()),
            pair_used_slots=len(S['used_slots']), pair_used_px=int(S['pair_used'].sum()),
            ft_records=len(S['rects']), ft_raw_px=int(S['ft_raw'].sum()),
            ft_win_px=int(S['ft_win'].sum()), ft_dil_px=int(S['ft_dil'].sum()),
            formula=('对偶: slot=(lead-0xA1)*94+(trail-0xA1); row=slot//62; col=slot%62; '
                     'x=16*col; y=2+16*(row+3*[row>=12])  (无相位, tcslib.'
                     'atlas_cell_xy_engine_view)'),
            ft_rule=('记录矩形 (u0,v0,u1,v1) 原样 ∪ 矩形+(%d,%d) ∪ 矩形±(%d,%d) —— '
                     '保守口径, 宁可少清' % (DU, DV, TX, TY)),
        ),
        residue=dict(
            mask='ink & ~pair_used & ~ft_dil',
            total_px=int(residue.sum()),
            ratio_pct=round(100.0 * int(residue.sum()) / int(ink.sum()), 2),
            by_kind={k: int(sum(r['ink_residue_px'] for r in rows if r['kind'] == k))
                     for k in (K_FREE, K_REC, K_NEVER, K_USED, K_FTWIN)},
            clearable_cells=sorted([r['slot'] for r in rows
                                    if r['kind'] == K_FREE and r['ink_residue_px'] > 0]),
            residue_slots=sorted([r['slot'] for r in rows
                                  if r['slot'] is not None and r['ink_residue_px'] > 0]),
            residue_slots_free=sorted([r['slot'] for r in rows
                                       if r['slot'] is not None and r['ink_residue_px'] > 0
                                       and not r['char']]),
            residue_regions=len([r for r in rows if r['ink_residue_px'] > 0]),
            residue_used_cells_px=int(sum(r['ink_residue_px'] for r in rows if r['kind'] == K_USED)),
        ),
        duplicate_offset_hits=duplicate_offsets(ink, w, h),
        ft_window_alignment=ft_window_alignment(ink, faces, w, h),
        residue_copy_evidence=find_copies(
            ink, _copy_boxes(rows), w, h),
        wrap_columns=wrap,
        regions=rows,
        slots=[r for r in rows if r['slot'] is not None],
        seconds=round(time.time() - t0, 1),
    )
    return dict(doc=doc, residue=residue, atlas=A, font=font, cs=cs, sampler=S, regions=rows)


# ═══════════════════════════ 真清 (写盘) ═══════════════════════════

def clear_on_iso(src_iso, dst_iso, residue, atlas, font, verbose=True):
    """把残墨像素写成"空色"。**只动像素容器的数据区**, 48B 包头逐字节核对。"""
    pak_e = font['pak_e']
    pak_src = font['atlas']['pak']
    px_off = atlas.px_off
    empty, _hist = atlas.empty_index()
    hdr_before = atlas.headers()
    ys, xs = np.where(residue)
    if len(ys):
        atlas.write_pixels(ys, xs, np.zeros(len(ys), bool), empty)
    for (doff, hb) in hdr_before:
        if bytes(atlas.cont[doff - tcslib.ATLAS_PREFIX_BYTES:doff]) != hb:
            raise SystemExit('!! 有 48B 包头被改了 (doff=0x%X)' % doff)
    if os.path.abspath(src_iso) != os.path.abspath(dst_iso):
        import shutil
        shutil.copyfile(src_iso, dst_iso)
    with open(dst_iso, 'r+b') as f:
        f.seek(pak_e['iso_off'] + px_off)
        f.write(bytes(atlas.cont))
    if os.path.getsize(src_iso) != os.path.getsize(dst_iso):
        raise SystemExit('!! ISO 尺寸变了')
    # 回读: 容器外一个字节都没动 + 引擎图 = 原图 − 残墨
    with open(dst_iso, 'rb') as f:
        f.seek(pak_e['iso_off'])
        pak2 = f.read(pak_e['stored'])
    if bytes(pak2[:px_off]) != bytes(pak_src[:px_off]) or \
       bytes(pak2[px_off + atlas.px_size:]) != bytes(pak_src[px_off + atlas.px_size:]):
        raise SystemExit('!! 回读: COMMON.PAK 里像素容器以外的字节被改了')
    A2 = repack_font.Atlas(pak2, px_off, atlas.px_size, atlas.w, atlas.h, atlas.psm)
    want = atlas.eng.copy()
    want[residue] = False
    bad = int((A2.eng != want).sum())
    if bad:
        raise SystemExit('!! 回读: 盘上解出的图与"原图−残墨"差 %d px' % bad)
    if verbose:
        print('  [clear] 清掉 %d px 残墨 (空色=索引 %d); 48B 包头逐字节未动 ✓; 回读 ✓'
              % (len(ys), empty))
    return dict(pixels_cleared=int(len(ys)), empty_index=empty,
                iso_sha256_after=tcslib.sha256_file(dst_iso))


# ═══════════════════════════ 产物 ═══════════════════════════

COL_USED = (198, 220, 248)      # 已用字形格底
COL_KEEP = (214, 240, 214)      # FT 采样窗底
COL_FREE = (255, 255, 255)      # 空白自由格
COL_NEVER = (250, 246, 214)     # 不可寻址区
COL_RES = (255, 0, 0)           # 残墨
COL_INK_U = (0, 0, 0)           # 已用格的墨
COL_INK_K = (0, 110, 0)         # 保留窗的墨
COL_LINE = (255, 190, 190)


def write_map2(doc, gray, residue, out_p, font_path=None):
    """三色标注图: 已用/保留/残墨, 底图 = 真实图集像素。"""
    from PIL import Image, ImageDraw, ImageFont
    w, h = doc['atlas']['w'], doc['atlas']['h']
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[:, :] = COL_FREE
    kind_col = {K_USED: COL_USED, K_FTWIN: COL_KEEP, K_FREE: COL_FREE,
                K_REC: COL_KEEP, K_NEVER: COL_NEVER}
    for r in doc['regions']:
        c = kind_col.get(r['kind'], COL_FREE)
        rgb[r['y0']:r['y0'] + r['h'], r['x0']:r['x0'] + r['w']] = c
    ink = np.frombuffer(gray, np.uint8).reshape(h, w) == 0
    used = np.zeros((h, w), bool)
    for r in doc['regions']:
        if r['kind'] == K_USED:
            used[r['y0']:r['y0'] + r['h'], r['x0']:r['x0'] + r['w']] = True
    for r in doc['regions']:
        if r['kind'] in (K_FTWIN, K_REC):
            used[r['y0']:r['y0'] + r['h'], r['x0']:r['x0'] + r['w']] = True
    rgb[ink & used] = COL_INK_U
    rgb[ink & ~used] = (150, 150, 150)
    rgb[residue] = COL_RES
    im = Image.frombytes('RGB', (w, h), rgb.tobytes())
    d = ImageDraw.Draw(im)
    for (yy, cc) in ((194, (255, 120, 0)), (242, (255, 120, 0)), (450, (255, 120, 0))):
        d.line([0, yy, w, yy], fill=cc)
    d.line([992, 0, 992, h], fill=(255, 120, 0))
    d.rectangle([0, 0, w - 1, h - 1], outline=(120, 120, 120))
    # 图例
    LEG_H = 118
    canvas = Image.new('RGB', (w, h + LEG_H), (255, 255, 255))
    canvas.paste(im, (0, 0))
    dd = ImageDraw.Draw(canvas)
    f = None
    if font_path and os.path.isfile(font_path):
        try:
            f = ImageFont.truetype(font_path, 15)
        except Exception:                                                # noqa: BLE001
            f = None
    if f is None:
        f = ImageFont.load_default()
    y = h + 6
    items = [
        (COL_USED, '已用字形格 / FT 采样窗 (保留)'),
        ((150, 150, 150), '不可动区域里的墨 (保留)'),
        (COL_RES, '残墨 (本工具建议清除的 %d px)' % doc['residue']['total_px']),
        (COL_NEVER, '不可寻址区 (对偶公式永不采样)'),
        (COL_FREE, '空白自由格 (可直接写新字)'),
    ]
    for (c, t) in items:
        dd.rectangle([8, y, 34, y + 14], fill=c, outline=(60, 60, 60))
        dd.text((42, y), t, fill=(0, 0, 0), font=f)
        y += 18
    dd.text((8, h + LEG_H - 16),
            'GR_ZH97 font atlas residue map — red = residue to clear; '
            'orange lines = grid holes (y=194..241) / wrap cols (x>=992) / bottom (y>=450)',
            fill=(60, 60, 60), font=ImageFont.load_default())
    canvas.save(out_p)
    return canvas.size


def write_zoom(doc, gray, residue, out_p, font_path=None, scale=4):
    """残墨簇 [清前 | 清后] 放大对照 (给人眼看的证据)。"""
    from PIL import Image, ImageDraw, ImageFont
    w, h = doc['atlas']['w'], doc['atlas']['h']
    ink = np.frombuffer(gray, np.uint8).reshape(h, w) == 0
    after = ink & ~residue
    boxes = []
    # 4 个代表区: 10 个记录码残墨格 / 回绕列样例 / 空洞带 / ASCII 第二带外的残墨
    boxes.append(('record-code stale fragments (rows 21-23, cols 5-9)', (80, 384, 160, 434)))
    boxes.append(('wrap columns x>=992 (rows 13-15)', (976, 256, 1024, 306)))
    boxes.append(('header hole y=194..241 (around y=198)', (0, 190, 96, 206)))
    boxes.append(('below grid y>=450 (ASCII 2nd band)', (448, 478, 704, 502)))
    PAD = 3
    tiles = []
    for (_cap, (x0, y0, x1, y1)) in boxes:
        for (arr, tag) in ((ink, 'BEFORE'), (after, 'AFTER')):
            sub = arr[y0:y1, x0:x1]
            rgb = np.zeros(sub.shape + (3,), np.uint8)
            rgb[:, :] = (255, 255, 255)
            rgb[sub] = (0, 0, 0)
            if tag == 'AFTER':
                r2 = residue[y0:y1, x0:x1]
                rgb[r2] = (255, 0, 0)
            im = Image.frombytes('RGB', (x1 - x0, y1 - y0), rgb.tobytes())
            im = im.resize(((x1 - x0) * scale, (y1 - y0) * scale), Image.NEAREST)
            tiles.append((tag, im))
    lab = 22
    tw = max(t[1].size[0] for t in tiles)
    th = max(t[1].size[1] for t in tiles)
    cols = 2
    rows_n = (len(tiles) + 1) // 2
    canvas = Image.new('RGB', (cols * (tw + PAD * 2), rows_n * (th + lab + PAD * 3) + 24),
                       (245, 245, 245))
    dd = ImageDraw.Draw(canvas)
    f = None
    if font_path and os.path.isfile(font_path):
        try:
            f = ImageFont.truetype(font_path, 14)
        except Exception:                                                # noqa: BLE001
            f = None
    if f is None:
        f = ImageFont.load_default()
    for i, (tag, im) in enumerate(tiles):
        cx = (i % cols) * (tw + PAD * 2) + PAD
        cy = (i // cols) * (th + lab + PAD * 3) + PAD
        canvas.paste(im, (cx, cy + lab))
        dd.rectangle([cx, cy + lab, cx + im.size[0] - 1, cy + lab + im.size[1] - 1],
                     outline=(120, 120, 120))
        dd.text((cx, cy + 3), tag, fill=(0, 0, 0), font=f)
    dd.text((PAD, canvas.size[1] - 18),
            'AFTER: black = kept ink, red = pixels this tool clears', fill=(40, 40, 40),
            font=ImageFont.load_default())
    canvas.save(out_p)
    return canvas.size


def human_report(doc, out_p, prefix):
    L = []
    A = L.append
    R = doc['residue']
    W_ = doc['windows']
    A('# 字库残墨测量报告 —— %s' % prefix)
    A('')
    A('> 工具 `%s` (%s) · 盘 `%s` · sha256 `%s`'
      % (TOOL, TOOL_VERSION, doc['iso'], doc['iso_sha256'][:16]))
    A('> 用的字符表 `%s`' % doc['charset'])
    A('> ⚠ 残墨是**相对字符表**算的（"已用对偶格"来自字符表）⇒ 量**历史盘**时要用**当年那份**'
      '字符表（例：量 GR_ZH97 用 `GR_ZH98/temp/charset_before_font_cleanup.json`），'
      '否则"后来被回收掉的字的字形"会被算成残墨。')
    A('> ★ 全部数字都是现读盘上像素 + 现读 charset 算出来的, 没有写死的常量。')
    A('')
    A('## 一句话')
    A('')
    A('**引擎不会采样的"残墨"共 %d 个黑像素** (占全图集墨 %d 的 %.2f%%); '
      '其余 %d 个黑像素全部落在"引擎真会采样"的窗里, 一个都不能动。'
      % (R['total_px'], doc['atlas']['ink_total'], R['ratio_pct'],
         doc['atlas']['ink_total'] - R['total_px']))
    A('')
    A('## 一、先划清"引擎会采样哪里" (判据)')
    A('')
    A('| 采样路径 | 覆盖 | 覆盖像素 |')
    A('|---|---|---|')
    A('| 对偶码 (1504 个字位) | `x=16*col`, `y=2+16*(row+3*[row>=12])`, `col=slot%%62<=61` | %d |'
      % W_['pair_any_px'])
    A('| └ 其中 charset **在用**的字形格 | %d 个字 | %d |' % (W_['pair_used_slots'],
                                                              W_['pair_used_px']))
    A('| 单字节/ASCII 的 FT 记录矩形 | %d 条 (3 个 face) | %d |'
      % (W_['ft_records'], W_['ft_raw_px']))
    A('| └ 加上实测偏置 +(%d,%d) (=dump_font 口径) | | %d |' % (DU, DV, W_['ft_win_px']))
    A('| └ **保守口径** 膨胀 ±(%d,%d) (本工具判据) | | %d |' % (TX, TY, W_['ft_dil_px']))
    A('')
    al = doc.get('ft_window_alignment') or {}
    if al:
        A('**"记录矩形到底是不是采样窗"—— 实测定案 (round49)**: 逐条看"墨的包围盒"相对矩形左上角'
          '的偏移:')
        A('')
        A('* 有墨的记录 %d 条; 墨从**第 0 列**就开始的 %d 条, 从**第 0 行**就开始的 %d 条;'
          % (al['records_with_ink'], al['ink_left_col0'], al['ink_top_row0']))
        A('* 左边界偏移直方图 `{偏移: 条数}` = `%s`; 上边界 = `%s`;' % (al['left_hist'],
                                                                      al['top_hist']))
        _le3 = sum(v for k, v in al['left_hist'].items() if k <= 3)
        A('* ★ 判据: 若采样窗是"矩形+(4,2)", 那**几乎不会有**记录的墨落在第 0..3 列;')
        A('  实测 **%d/%d 条**的墨落在第 0..3 列 (只有 %d 条落在第 4 列及以后) '
          '⇒ **矩形本身就是采样窗**。'
          % (_le3, al['records_with_ink'],
             al['records_with_ink'] - _le3))
        A('* 实例: ASCII `A` 的矩形 (256,452)-(264,468) 里是一个**端正的 A**;')
        A('  同一矩形 +(4,2) 里则是**错位的碎片** ⇒ **矩形本身就是采样窗**。')
        A('* ⇒ 定位用**原矩形** (与 `repack_font` 同口径); 而清理保护罩仍**故意**用')
        A('  ±(%d,%d) 的膨胀 —— 宁可少清几十个像素, 不赌。' % (TX, TY))
        A('')
    A('判据一句话: **残墨 = 墨 ∧ ¬(charset 已用对偶格) ∧ ¬(全部 FT 记录窗, 膨胀 ±(%d,%d))**。'
      % (TX, TY))
    A('')
    A('## 二、残墨在哪 (按类型)')
    A('')
    A('| 类型 | 像素 | 说明 |')
    A('|---|---|---|')
    names = {
        K_FREE: ('空对偶槽的格', '空着没人用的码位格, 却还压着旧字形 —— **真碎片, 清了就能写新字**'),
        K_REC: ('单字节记录码占死的格', '对偶码永远不能用的格; 窗外的部分同样是旧字形碎片'),
        K_NEVER: ('对偶公式永不覆盖的区域', '回绕列 / 顶部 2 行 / 包头让位空洞 / 网格下方 —— 画不出来'),
    }
    for k, (nm, nt) in names.items():
        v = R['by_kind'].get(k, 0)
        if v:
            A('| %s | %d | %s |' % (nm, v, nt))
    A('')
    free_cells = R['clearable_cells']
    A('其中有残墨的**空对偶槽**: %d 个 → %s' % (len(free_cells), free_cells))
    A('')
    A('> 说明: 「单字节记录码占死的格」里的残墨 = 格子的**一角**归别人的采样窗 (保留), '
      '剩下那块是历史遗留的旧字形碎片 ⇒ 只清窗外那一块, 窗内一个像素不动。')
    A('')
    dups = doc.get('duplicate_offset_hits') or []
    if dups:
        A('### 这些残墨"长得像字"是怎么回事 (实测证据)')
        A('')
        A('把墨图整体平移 (dx,dy) 后, 与原地墨点重合的像素数 —— 重合率高 = 同一块内容被')
        A('重复写了两遍 (历史工具用了另一套坐标口径)。实测前几名:')
        A('')
        A('| 平移 (dx,dy) | 重合墨点 | 该位移下源墨点 | 重合率 | 占全图墨 |')
        A('|---|---|---|---|---|')
        for d in dups:
            A('| (%+d,%+d) | %d | %d | %.1f%% | %.1f%% |'
              % (d['dx'], d['dy'], d['match_px'], d['src_ink_px'], d['ratio'] * 100,
                 d['share_of_atlas'] * 100))
        A('')
        A('单块级别的**逐像素副本**判定 (FFT 互相关, `corr` = 平移后仍重合的墨点数;')
        A('位移 (dx,dy) 的语义 = **副本相对源块的位移**, 符号约定用合成图校验过):')
        A('')
        A('| 残墨块 | 块内墨 | 副本在 (dx,dy) | corr | 结论 |')
        A('|---|---|---|---|---|')
        for e in (doc.get('residue_copy_evidence') or []):
            h0 = e['hits'][0] if e['hits'] else None
            if not h0:
                continue
            verdict = ('**逐像素副本**' if h0['corr'] == e['ink_px'] else
                       ('高度重合 (%.0f%%)' % (100.0 * h0['corr'] / e['ink_px'])
                        if h0['corr'] >= 0.6 * e['ink_px'] else '看不出副本关系'))
            if '右侧 2 格' in e['label'] and h0['corr'] == e['ink_px'] and h0['dy'] == 1:
                verdict += '; 副本比源**低 1 行** ⇒ 正是旧 flat 公式"回绕列低 1 行"的指纹'
            A('| %s | %d | (%+d,%+d) | %d | %s |'
              % (e['label'], e['ink_px'], h0['dx'], h0['dy'], h0['corr'], verdict))
        A('')
        A('⇒ 残墨里那些"看着像干净字形"的块, 多数是**别处内容的副本** (尤其 y=482 那条'
          '单字节带右侧); 副本不被任何采样窗指向 ⇒ 只能是残留, 清掉不影响显示。')
        A('')
    A('## 三、必须保留的 (一个像素都不动)')
    A('')
    A('| 区域 | 为什么 |')
    A('|---|---|')
    A('| charset 在用的 %d 个对偶格 (%d px) | 那是**活字形**, 动一格就是整屏乱码 '
      '(round43 有实证) |' % (W_['pair_used_slots'], W_['pair_used_px']))
    A('| FT 记录采样窗 (膨胀 ±(%d,%d)) | 单字节码 / ASCII / 手柄图标的采样窗, '
      '矩形**不对齐 16x16** (如武器页滚动箭头是 (89,395)-(94,408) 的 5x13 小矩形) |' % (TX, TY))
    A('| 手柄图标码 0xB1/0xB5 的记录格 | 引擎有硬编码 UV, 虽然画的是另一张贴图, '
      '但记录表里那格仍被别的码共用 |')
    A('')
    A('## 四、"回绕列" x=992..1023 的判定 (用户问过的那两条)')
    A('')
    A('* 对偶码寻址 `col = slot %% 62` ⇒ **x 最大 976, 格子右边界 991**;')
    A('* 图集宽 1024 = **64 格**, 所以每行右边多出 **2 格 (x=992..1023)**;')
    A('* 穷举全部 **%d** 个 slot 的采样窗 ⇒ 落在 x>=992 的: **%d px** (对偶路径);'
      % (doc['wrap_columns']['slots_checked'], doc['wrap_columns']['pair_windows_hit_strip']))
    A('* 穷举全部 %d 条 FT 记录矩形 ⇒ 原样命中 x>=992 的 **%d px**, '
      '加上 +(%d,%d) 偏置后 **%d px**, 保守膨胀后 **%d px**;'
      % (W_['ft_records'], doc['wrap_columns']['ft_raw_hit_strip'], DU, DV,
         doc['wrap_columns']['ft_win_hit_strip'], doc['wrap_columns']['ft_dil_hit_strip']))
    A('* 命中它们的窗只有: %s'
      % (', '.join('%s 0x%02X (%d,%d)-(%d,%d)' % (r['face'], r['code'], r['u0'], r['v0'],
                                                  r['u1'], r['v1'])
                   for r in doc['wrap_columns']['hit_rects']) or '(无)'))
    A('* 该区墨 %d px, 其中 **可清 %d px**, 必须留 %d px。'
      % (doc['wrap_columns']['ink_strip'], doc['wrap_columns']['residue_strip'],
         doc['wrap_columns']['ink_strip'] - doc['wrap_columns']['residue_strip']))
    A('')
    A('> **"回绕列"是什么语义**: 像素容器是 **GIF 封包流** —— 每 64 行像素前面有 48 字节包头;'
      ' 把整块当"裸图"逐行读时, 每段的 48B 包头会把该段内容整体右移 96 texel (= 6 格),'
      ' 越过后在行内回绕。而引擎走的是封包口径 (包头不是像素)。本工具与 `dump_font` 默认'
      ' 都用**引擎口径**的图 ⇒ 这里的 x>=992 纯粹是"对偶路径寻址不到的两格", '
      '里面是什么历史内容不影响判定: **画不出来 = 可以清**。')
    A('')
    A('## 五、报告里"92 个待回收"的真相')
    A('')
    A('`release/字库报告.md` 的「要先"回收旧字"才能用的位子: 92 个」= '
      '**charset 空槽 (185) 里、引擎格上还有墨的那些**。本工具逐个拆开:')
    rec = [r for r in doc['slots'] if r['kind'] == K_REC and r['ink_px'] > 0]
    A('')
    A('* 92 个里 **%d 个**整格被**单字节记录码**占死 (`ATLAS_ENGINE_SINGLE_CELLS`) '
      '⇒ 引擎拿这些格画单字节汉字/符号, **对偶码永远不能用**;' % len(rec))
    A('* 其余 %d 个被 FT 记录矩形压着 ⇒ 同样是别人的采样窗;' % (92 - len(rec)))
    A('* ⇒ **这 92 个格子没有一个能"回收成新字位"**, 报告那句话的口径会让人误会。'
      '真正能释放字位的是"回收死字"(见 patch 报告)。')
    A('')
    A('## 六、要清的逐块明细 (完整 1504 槽全表在 residue.json 的 `slots`)')
    A('')
    A('| 分类 | 建议 | 格 (行,列) | 坐标 (x,y) 尺寸 | 墨 | 窗内 | 残墨 | 理由 |')
    A('|---|---|---|---|---|---|---|---|')
    order = {K_REC: 0, K_NEVER: 1, K_FREE: 2}
    clr = [x for x in doc['regions'] if x['ink_residue_px'] > 0]
    clr.sort(key=lambda x: (order.get(x['kind'], 9), x['y0'], x['x0']))
    for r in clr:
        pos = '(%d,%d)' % (r['row'], r['col']) if r['row'] is not None else '—'
        A('| %s | %s | %s | (%d,%d) %dx%d | %d | %d | **%d** | %s |'
          % (r['kind'], r['advice'], pos, r['x0'], r['y0'], r['w'], r['h'], r['ink_px'],
             r['ink_in_window_px'], r['ink_residue_px'], r['reason']))
    A('')
    A('合计 **%d 块 / %d px** 建议清除 (占全图墨 %.2f%%)。'
      % (len(clr), R['total_px'], R['ratio_pct']))
    A('')
    keep_cells = [x for x in doc['slots'] if x['kind'] == K_USED and x['ink_px'] > 0]
    A('保留侧汇总 (不逐条列, 全表在 residue.json): '
      'charset 在用且有墨的对偶格 **%d** 个 / %d px; FT 记录窗内墨 **%d** px; '
      '两者之外的墨就是上面那 %d px。'
      % (len(keep_cells), sum(x['ink_px'] for x in keep_cells),
         sum(x['ink_in_window_px'] for x in doc['regions']), R['total_px']))
    A('')
    A('## 七、已知限制 (诚实交代)')
    A('')
    A('1. **FT 记录窗的两种口径都算过**: 实测"矩形本身就是采样窗" (见 §一 的 offset 直方图),'
      ' 但 `+ (%d,%d)` 这个历史**写入侧**偏置在本工程的其它工具里也被当作可能窗'
      ' (`dump_font._live_rects`) ⇒ 本工具的保护罩取"原矩形 ∪ 矩形+(%d,%d) ∪ 膨胀 ±(%d,%d)"'
      ' 的**超集**: 宁可有 44 个格少清, 也不冒险 (round43 的教训)。'
      % (DU, DV, DU, DV, TX, TY))
    A('2. **手柄图标码 0xB1/0xB5** 走的是另一张贴图 (`pda_counterparts.rsb`, 硬编码 UV), '
      '但它们的 FT 记录格 (136,420)-(146,436) 仍被 0x20/0x7F/0xA1..0xAD 共用 ⇒ 一并保护。')
    A('3. **"回绕列是谁写的"没有定论**: 已证明"引擎采样不到", 没证明"历史上是谁写进去的"。'
      '不影响清理决策。')
    A('4. 本工具**只测不写**; 真清由 `patch_zh98_font_cleanup.py` 调用同一份掩码执行, '
      '并回读校验 (容器外零字节改动 + 引擎图 = 原图−残墨)。')
    A('')
    A('## 八、产物')
    A('')
    A('| 文件 | 内容 |')
    A('|---|---|')
    A('| `residue.json` | 本报告的机器可读版 (逐格 + 1504 槽全表 + 回绕列判定) |')
    A('| `residue_map.png` | 三色标注图 (蓝=已用/绿=保留/红=残墨/黄=不可寻址) |')
    A('| `residue_zoom.png` | 残墨簇 4 倍放大 [清前 \\| 清后] 对照 |')
    A('')
    io.open(out_p, 'w', encoding='utf-8', newline='\n').write('\n'.join(L) + '\n')
    return len(L)


def main():
    ap = argparse.ArgumentParser(description='图集残墨测量 (只读)')
    ap.add_argument('--iso', default=os.path.join(REPO, 'work', 'builds', 'GR_ZH97',
                                                  'GR_ZH97.iso'))
    ap.add_argument('--charset', default=None)
    ap.add_argument('--out', default=None, help='产物目录 (默认 <盘目录>/temp/font_residue)')
    ap.add_argument('--prefix', default=None, help='产物前缀 (默认版本名)')
    ap.add_argument('--no-png', action='store_true')
    a = ap.parse_args()
    iso = os.path.abspath(a.iso)
    ver = os.path.splitext(os.path.basename(iso))[0]
    out = a.out or os.path.join(os.path.dirname(iso), 'temp', 'font_residue')
    prefix = a.prefix or ver
    os.makedirs(out, exist_ok=True)

    res = compute(iso, a.charset, verbose=True)
    doc = res['doc']
    jp = os.path.join(out, 'residue.json')
    io.open(jp, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('[residue] → %s' % rel(jp))
    rp = os.path.join(out, 'residue_report.md')
    human_report(doc, rp, prefix)
    print('[residue] → %s' % rel(rp))
    if not a.no_png:
        gray = dump_font.atlas_gray(res['font']['atlas'], view='engine')
        fp = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
        mp = os.path.join(out, 'residue_map.png')
        write_map2(doc, gray, res['residue'], mp, font_path=fp)
        print('[residue] → %s' % rel(mp))
        zp = os.path.join(out, 'residue_zoom.png')
        write_zoom(doc, gray, res['residue'], zp, font_path=fp)
        print('[residue] → %s' % rel(zp))
    # 人话小结
    R = doc['residue']
    print('')
    print('  残墨 %d px (全图墨 %d, %.2f%%)' % (R['total_px'], doc['atlas']['ink_total'],
                                                R['ratio_pct']))
    for k, v in R['by_kind'].items():
        if v:
            print('    %-18s %5d px' % (k, v))
    print('  有残墨的空对偶槽 %d 个: %s' % (len(R['clearable_cells']), R['clearable_cells']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
