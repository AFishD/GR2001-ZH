# -*- coding: utf-8 -*-
r"""patch_zh109_edge_fix.py — round59: 把落在贴图右缘 (x >= 992) 的 FT 记录矩形搬回安全区

## 现象 (用户实机, 训练7 教程页)

教程页 `EN_STRINGS.RES@MENU+GR.IMG#902` 的 `LANG:G012.I023` / `G013.I023`
(「你的小队分为两个战斗小组…选中一个战斗小组…」) 里 **「个」渲染成斜纹方块**, 同句其它字正常。

## 根因 (round59 只读复核, 数字见 work/builds/GR_ZH98/temp/r59/recon_zh109.{log,json})

  · 「个」= 单字节码 **0xEE**, 文本对、字形对:
    GR_ZH98 (搬字前) rec=(288,354,304,370) 框内 26 px; 现役 GR_ZH108 rec=(1008,195,1024,211)
    框内 **同样 26 px 且与旧位置逐像素相等**; 旧位置已清空; `pad`/`advance` = 0/16 未动。
  · 记录矩形落点 = **round54 搬字 (patch_zh104_relocate.py) 的 64 列布局**:
    `BAND_Y=(195,211)`, `x_step=16`, `W//CW = 64` 列 ⇒ x = 0,16,…,**1008**。
    「个」是那批里 code 最大的 16x16 字形 (第 64 格) ⇒ 正好被放到 **x=1008…1024**。
  · **安全上界 = x ≤ 976 (u1 ≤ 992)**, 三条互相独立的证据:
      ① 引擎自己的字形网格公式 `tcslib.atlas_cell_xy_engine_view`: `col = slot % 62 ≤ 61`
         ⇒ x = 16*col ≤ **976** —— 引擎寻址到的最右一列就是 x=976;
      ② 实机反证 (同一页!): 同批搬走的 **0xEC「选」在 (976,195,992,211)** (u1=992) 显示正常
         (该页「**选中**一个战斗小组」的「选」), 而「个」(u1=1024) 是斜纹方块
         ⇒ 「u1 ≤ 992 能取到」是**用户肉眼验证过**的;
      ③ 历史包线: 搬字前的 GR_ZH98 上, 3 个 face 全部 544 条非退化矩形的 max(u1) = **992**
         (GR_EN_ORIG 是 512 宽贴图, max(u1)=513) —— "矩形右缘压到贴图右边界"是 round54 才第一次出现。
  · 现役盘上 u1 > 992 的记录共 **22 条 × 2 face (huge 面只有 0x20/0x7F)**:
      0x20 0x7F 0xA1..0xAD (17 条,**10x16 空矩形**, 全是 0 墨: 空格/未用码/对偶 lead/图标码)
      0xAE 0xAF 0xB0 (16x16 空矩形, 0 墨; round55 只改记录表、把它们的矩形指到了空区)
      **0xED「这」 (992,195,1008,211) 54 px** 与 **0xEE「个」 (1008,195,1024,211) 26 px** —— 只有这 2 条有墨,
      其中**唯一**右缘 = 贴图宽度 (u1=1024) 的就是「个」 ⇒ 与用户看到的唯一坏字完全吻合。

## 修法 (只动记录矩形 + 那 2 条的字形像素, 一个别的字节都不碰)

  · **所有 u0 ≥ 992 的非退化记录** ⇒ 一律搬到 `x ≤ 976` 的安全空位 (保尺寸):
      - 有墨的 (0xED / 0xEE): 各占一个 16x16 空格, **像素逐像素搬过去**, 旧位置清空;
      - 空的 16x16 (0xAE / 0xAF / 0xB0): 各占一个 16x16 空格 (它们是"还能用的单字节码",
        留成独立矩形, 免得以后给其中一个写真字形时连累另两个); 旧/新都是 0 墨;
      - 空的 10x16 (0x20 0x7F 0xA1..0xAD 0xB1 0xB5): 今天**共用同一个矩形**, 整组共用一个新空矩形
        (空白 → 空白, 画面必然不变; 搬它们只为把"任何记录矩形都不得越过 x=976"做成硬不变量)。
  · 落点 = 搬字带 `y=195/211` 里 `x ≤ 976` 的 **无墨 / 不被任何对偶槽位覆盖 / 不被任何记录覆盖** 的
    连续空格 (确定性扫描: y 升序、x 升序, 取第一个装得下的位置)。不新开区域、不动对偶网格。

## 硬断言 (写盘前)

  ① 每个新矩形: 写前 0 墨、不被任何对偶槽位覆盖 (全部 1504 个, 不只"在用"的)、
     不被任何其它记录矩形覆盖、与其它新矩形互不重叠、尺寸与旧矩形逐条相同;
  ② 待清像素只落在旧矩形内, 且旧矩形 ∩ 在用对偶格 = 0、∩ **别的**记录矩形 = 0
     (有墨的记录被清之前它的像素一定先被搬到新位置);
  ③ 保护区 (1175 个在用对偶格 ∪ 其它记录矩形) 与"改动像素"交集 = 0;
  ④ 改动像素只落在 (旧矩形 ∪ 新矩形) 内;
  ⑤ `pad`(rec[0]) / `advance`(rec[1]) **一个字节都不动** —— 只改 u/v;
  ⑥ 搬完以后, 3 个 face 的**全部**非退化记录 max(u1) ≤ 992。

## 回读自检 (写盘后, 用另一份 `load_font` 重新从盘上装载)

  · 旧矩形墨 = 0; 新矩形与旧像素**逐像素相等**;
  · 保护区 丢失 0 / 新增 0; 改动像素只落在 (旧 ∪ 新);
  · 记录: 被搬的 u/v = 新矩形、pad/advance 原值; **其它记录逐字节不变**;
  · 像素容器 48B 包头逐字节不变; COMMON.PAK 像素容器外 / FONT.RES 槽外零改动;
  · 幂等: 再跑一次 ⇒ 候选 0 条 ⇒ 0 改动 (产物与输入逐字节相同)。

## 用法

  python tools/iso_build/patch_zh109_edge_fix.py <src.iso> <dst.iso> [--report <json>] [--dry-run]

  ⚠ 只接受"已经搬过字、且存在越过 x=976 的记录"的盘 (即 GR_ZH104..GR_ZH108 这条线)。
    候选集与预期不符 (多/少) ⇒ **直接报错退出**, 不猜、不硬改。
"""
import argparse
import io
import json
import os
import shutil
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
except Exception:                                                    # noqa: BLE001
    pass

import csv                                                           # noqa: E402
import dump_font as D                                                # noqa: E402
import tcslib                                                        # noqa: E402
from patch_zh94_glyph_align import Atlas                             # noqa: E402
from patch_zh104_relocate import face_tables                         # noqa: E402  (同一份 face 解析)

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
TEXT_DEFAULT = os.path.join(REPO, 'work', 'builds', 'GR_ZH108', 'text')
FACE_ORDER = ['large', 'default', 'huge']
W, H = 1024, 512
CW = CH = tcslib.CW
EMPTY_NIB = 1                      # 现役容器的背景 nibble (= 封包填充 0x11)
SAFE_X_MAX = 976                   # ★ 安全上界: 矩形左缘 x ≤ 976 (u1 ≤ 992)
EDGE_U0 = 992                      # 越过这条线就算"压到贴图右缘"
BAND_Y = (195, 211)                # 搬字带 (round54 用的两条 16 行带; 在 y=194 回绕行与行 12 之间)
FREE_Y0, FREE_Y1 = 194, 242        # 空区 (对偶网格之外): 行 11 结束于 y=193(+回绕行 194), 行 12 起于 242
PREF_Y = 213                       # ★ 落点行: 比带 1 的最后一行墨 (y≤210) 低 2 px, 又比带 2 低 2 px
HALO_X, HALO_Y = tcslib.GLYPH_TOL_X, tcslib.GLYPH_TOL_Y   # 4 / 2 —— dump_font 判"有墨"的容差邻域
#   ★ 为什么是 y=213 而不是 y=211: dump_font / 单格字库判"这条记录画得出来吗"时看的是
#     **矩形 + (4,2) 偏置 + ±(4,2) 邻域**。落点若贴着带 1 的字形墨, 那些**本来就该是空**的记录
#     (0x20/0x7F/0xA1..0xAD/0xAE/0xAF/0xB0/0xB1/0xB5) 会被邻域里的墨"染"成"有墨",
#     让字库 dump 的「无墨 42 条」这个对照数字变掉。取 y=213 + 落点间留出 ±(4,2) 间隔
#     ⇒ 这些空矩形的新邻域仍然干净, **有墨/无墨逐条不变**。
# 预期候选集 (u0 ≥ 992): 17 条空 10x16 共用矩形 + 3 条空 16x16 + 2 条有墨 16x16
EXPECT_CODES = [0x20, 0x7F] + list(range(0xA1, 0xAE)) + [0xAE, 0xAF, 0xB0, 0xB1, 0xB5, 0xED, 0xEE]
BLANK_SHARED = [0x20, 0x7F] + list(range(0xA1, 0xAE)) + [0xB1, 0xB5]      # 共用空矩形的 17 条
CANON = {0x7B: '{', 0x7D: '}', 0xE7: 'ç', 0xF1: 'ñ'}


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def text_occurrences(textdir):
    """正文出现次数 (判"活字形"用; 与 font_cell_map / patch_zh104 同口径)。读不到就返回 None。"""
    if not textdir or not os.path.isdir(textdir):
        return None
    occ = {}
    for fn in sorted(os.listdir(textdir)):
        if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
            with io.open(os.path.join(textdir, fn), encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    for ch in (row.get('text_edited') or ''):
                        occ[ch] = occ.get(ch, 0) + 1
    return occ or None


def load(iso):
    """只读装载: 3 个 face 的记录表 + 引擎口径图集 (bool 墨图) + 容器。"""
    w = D.load_font(iso)
    ad = w['atlas']
    assert (ad['w'], ad['h'], ad['psm']) == (W, H, 0x14), \
        '图集不是 1024x512 PSMT4: %s' % ((ad['w'], ad['h'], ad['psm']),)
    A = Atlas(bytearray(ad['pak']), ad['px_off'], ad['px_size'])
    assert A.eng.shape == (H, W)
    tables, _ft_end = face_tables(w['ft_blob'])
    names = [t[0] for t in tables]
    assert names == FACE_ORDER, 'face 顺序变了: %s' % names
    rec = {}                       # face → {code: (b0, b1, u0, v0, u1, v1)}
    for (nm, fld, off, nrec) in tables:
        d = {}
        for i in range(nrec):
            d[i + 0x20] = struct.unpack_from('<BB4H', w['ft_blob'], off + 10 * i)
        rec[nm] = d
    return dict(w=w, ad=ad, A=A, ink=A.eng, tables=tables, rec=rec)


def rect_of(r):
    """记录 → 非退化矩形 (u0,v0,u1,v1); 退化记录返回 None。"""
    if r is None or r[4] <= r[2] or r[5] <= r[3]:
        return None
    return (r[2], r[3], r[4], r[5])


def slot_mask():
    """全部 1504 个对偶槽位的引擎格 (图集内的部分) —— 新落点一个都不能压上去。"""
    m = np.zeros((H, W), dtype=bool)
    for s in range(tcslib.pair_capacity()):
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        if 0 <= x and x + CW <= W and 0 <= y and y + CH <= H:
            m[y:y + CH, x:x + CW] = True
    return m


def rect_mask(rects):
    m = np.zeros((H, W), dtype=bool)
    for (u0, v0, u1, v1) in rects:
        m[v0:v1, u0:u1] = True
    return m


def find_target(free, w_, h_, taken):
    """在空区 (y=194..241, x ≤ 976) 里找一块 w_ x h_ 的空位。

      · `free`  = 无墨 且 不在任何对偶槽位上 且 不在任何记录矩形上 (含待搬记录的旧矩形);
      · `taken` = 已经定下的落点 (含 ±(4,2) 容差间隔) ⇒ 落点之间不会互相"染"到;
      · 先取 **y=213** (见常量区: 保住 dump_font 的"有墨/无墨"逐条不变), 再退到空区里任意行;
      · x 先按 16 像素对齐扫, 再退一步按 2 像素扫 (碎片兜底); 只取 x ≤ 976。
    """
    rows = [PREF_Y] + [y for y in range(FREE_Y0, FREE_Y1 - h_ + 1) if y != PREF_Y]
    for step in (CW, 2):
        for y in rows:
            for x in range(0, SAFE_X_MAX + 1, step):
                if x + w_ > EDGE_U0:             # u1 = x + w_ ≤ 992
                    break
                blk = free[y:y + h_, x:x + w_]
                if blk.shape != (h_, w_) or not blk.all() or taken[y:y + h_, x:x + w_].any():
                    continue
                return (x, y, x + w_, y + h_)
    return None


def mark_taken(taken, rect):
    """把落点连同 ±(4,2) 的容差间隔一起标记为已占 (落点之间的最小间隔)。"""
    u0, v0, u1, v1 = rect
    taken[max(0, v0 - HALO_Y):min(H, v1 + HALO_Y),
          max(0, u0 - HALO_X):min(W, u1 + HALO_X)] = True


def build_plan(M, code2ch, occ, log):
    """扫描 u0 ≥ 992 的记录 → 搬运方案 (每条: 旧矩形 / 新矩形 / 涉及哪些 face / 墨量)。"""
    ink = M['ink']
    # ---- 候选: 全 face 汇总, 逐 code 核对矩形一致 ----
    cand = {}
    for nm in FACE_ORDER:
        for c, r in M['rec'][nm].items():
            rc = rect_of(r)
            if rc is None or rc[0] < EDGE_U0:
                continue
            cand.setdefault(c, {'faces': {}, 'rects': set()})
            cand[c]['faces'][nm] = rc
            cand[c]['rects'].add(rc)
    got = sorted(cand)
    if not got:
        log('候选 0 条 ⇒ 这张盘上**没有任何记录越过 x=%d** (已经修过了)' % SAFE_X_MAX)
        return [], None, None
    bad = {c: sorted(v['rects']) for c, v in cand.items() if len(v['rects']) != 1}
    assert not bad, ('这些码位在不同 face 里的矩形不一样, 需要逐 face 处理 (本补丁不猜): %s'
                     % json.dumps({'0x%02X' % c: v for c, v in bad.items()}, ensure_ascii=False))
    if got != EXPECT_CODES:
        log('!! 候选集与预期不符 (预期 %d 条 / 实得 %d 条)'
            % (len(EXPECT_CODES), len(got)))
        log('   预期: %s' % ' '.join('0x%02X' % c for c in EXPECT_CODES))
        log('   实得: %s' % ' '.join('0x%02X' % c for c in got))
        log('   多出来: %s' % (' '.join('0x%02X' % c for c in got if c not in EXPECT_CODES)
                               or '(无)'))
        log('   少了  : %s' % (' '.join('0x%02X' % c for c in EXPECT_CODES if c not in cand)
                               or '(无)'))
        raise SystemExit('!! 候选集不是本补丁认识的那一批 ⇒ 停下人工确认 (不硬改)')

    used = slot_mask()
    other_rects = [rc for nm in FACE_ORDER for c, r in M['rec'][nm].items()
                   if c not in cand and (rc := rect_of(r)) is not None]
    old_rects = [next(iter(v['rects'])) for v in cand.values()]
    # 自由区 = 无墨 且 不在任何对偶格上 且 不在任何记录矩形上 (含待搬记录的旧矩形)
    free = ~(ink | used | rect_mask(other_rects) | rect_mask(old_rects))

    taken = np.zeros((H, W), dtype=bool)
    moves = []
    shared = {}                                   # 空矩形一组的共同落点
    # 处理顺序 (确定性): 有墨的先拿最靠左的空格 → 空的 16x16 → 空 10x16 共用组
    def _n_ink(c):
        rc = next(iter(cand[c]['rects']))
        return int(ink[rc[1]:rc[3], rc[0]:rc[2]].sum())

    order = ([c for c in got if _n_ink(c) > 0]
             + [c for c in got if _n_ink(c) == 0 and c not in BLANK_SHARED]
             + [c for c in got if _n_ink(c) == 0 and c in BLANK_SHARED])
    assert sorted(order) == got, '处理顺序漏了候选'
    for c in order:
        rc = next(iter(cand[c]['rects']))
        w_, h_ = rc[2] - rc[0], rc[3] - rc[1]
        n_ink = _n_ink(c)
        key = None
        if n_ink == 0 and c in BLANK_SHARED:
            key = (w_, h_, rc)
            if key in shared:
                new = shared[key]
            else:
                new = find_target(free, w_, h_, taken)
                assert new, '0x%02X (%dx%d) 找不到安全空位' % (c, w_, h_)
                shared[key] = new
        else:
            new = find_target(free, w_, h_, taken)
            assert new, '0x%02X (%dx%d) 找不到安全空位' % (c, w_, h_)
        mark_taken(taken, new)                     # 落点 + ±(4,2) 间隔一并占掉
        ch = code2ch.get(c, CANON.get(c, ''))
        grp = [x for x in got if x != c and x in BLANK_SHARED
               and next(iter(cand[x]['rects'])) == rc]
        for x in grp:                              # 共用一组的旧矩形必须**逐条相同**
            assert (n_ink == 0
                    and int(ink[rc[1]:rc[3], rc[0]:rc[2]].sum()) == 0), \
                '0x%02X 与 0x%02X 想共用落点, 但矩形/内容不同' % (c, x)
        moves.append(dict(code=c, char=ch, w=w_, h=h_, old=list(rc), new=list(new),
                          faces=sorted(cand[c]['faces']), ink=n_ink,
                          live=bool(ch) and bool(occ and occ.get(ch, 0) > 0),
                          occ=(occ.get(ch, 0) if (occ and ch) else None),
                          shared_with=grp if key else []))
    return moves, used, other_rects


def check_plan(M, moves, used, other_rects, log):
    """写盘前硬断言 ①②③④ (见文件头)。"""
    ink = M['ink']
    old_mask = rect_mask([tuple(m['old']) for m in moves])
    new_mask = rect_mask([tuple(m['new']) for m in moves])
    other_mask = rect_mask(other_rects)
    n_old_rect = len(set(tuple(m['old']) for m in moves))

    # ① 旧矩形: 不压在格上 / 不压在别的记录上
    assert not (old_mask & used).any(), '待清像素落在**对偶槽位**里'
    assert not (old_mask & other_mask).any(), '待清像素落在**别的记录矩形**里'
    # ① 新矩形
    for m in moves:
        u0, v0, u1, v1 = m['new']
        assert (u1 - u0, v1 - v0) == (m['w'], m['h']), ('尺寸变了', m['code'])
        assert u1 <= EDGE_U0, ('新矩形右缘越过 x=992', m['code'], m['new'])
        assert 0 <= u0 and 0 <= v0 and u1 <= W and v1 <= H, ('新矩形出图', m['code'])
        assert not ink[v0:v1, u0:u1].any(), ('新矩形写前有墨', '0x%02X' % m['code'], m['new'],
                                            int(ink[v0:v1, u0:u1].sum()))
    assert not (new_mask & used).any(), '新矩形压在**对偶槽位**上'
    assert not (new_mask & other_mask).any(), '新矩形压在**别的记录矩形**上'
    assert not (new_mask & old_mask).any(), '新矩形压在旧矩形上'
    cnt = np.zeros((H, W), dtype=np.uint8)
    for rc in sorted(set(tuple(m['new']) for m in moves)):
        cnt[rc[1]:rc[3], rc[0]:rc[2]] += 1
    assert cnt.max() <= 1, '新矩形互相重叠 (%d 处)' % int((cnt > 1).sum())
    # ③ 保护区
    protect = used | other_mask
    assert not ((old_mask | new_mask) & protect).any(), '改动像素侵入保护区'
    # ④ 目标图
    tgt = ink.copy()
    for m in moves:
        u0, v0, u1, v1 = m['old']
        nu0, nv0, nu1, nv1 = m['new']
        tgt[nv0:nv1, nu0:nu1] = ink[v0:v1, u0:u1]
        tgt[v0:v1, u0:u1] = False
    diff = tgt != ink
    assert not (diff & protect).any(), '待写像素侵入保护区'
    assert not (diff & ~(old_mask | new_mask)).any(), '待写像素逸出 (旧 ∪ 新)'
    log('① 旧矩形 %d 个 (%d 条记录): ∩ 对偶槽位 0 ✓ ∩ 其它记录矩形 0 ✓'
        % (n_old_rect, len(moves)))
    log('② 新矩形 %d 个: 全部右缘 ≤ %d ✓ 互相不重叠 ✓ 尺寸逐条不变 ✓ 写前墨 0 ✓ '
        '∩ 对偶槽位(全部 %d 个) 0 ✓ ∩ 其它记录矩形 0 ✓'
        % (len(set(tuple(m['new']) for m in moves)), EDGE_U0, tcslib.pair_capacity()))
    log('③ 保护区 = 对偶格 %d px ∪ 其它记录矩形 %d px —— 与改动像素交集 0 ✓'
        % (int(used.sum()), int(other_mask.sum())))
    log('④ 待写像素 %d px (清 %d + 写 %d) —— 全部落在 (旧 ∪ 新) 内 ✓'
        % (int(diff.sum()), int((old_mask & diff).sum()), int((new_mask & diff).sum())))
    return tgt, diff, old_mask, new_mask, protect


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--report', default=None)
    ap.add_argument('--text', default=None, help='文本表目录 (判"活字形"用; 默认 GR_ZH108/text)')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src = a.src
    dst = a.dst or src
    textdir = a.text or TEXT_DEFAULT
    report = a.report or os.path.join(os.path.dirname(os.path.abspath(dst)),
                                      os.path.splitext(os.path.basename(dst))[0]
                                      + '_edge_fix_report.json')
    lines = []

    def log(s=''):
        print(s)
        lines.append(s)

    log('=' * 92)
    log('GR_ZH109 贴图右缘修复: 把 u0 ≥ %d 的 FT 记录矩形搬回 x ≤ %d (安全上界 = 对偶网格最右列)'
        % (EDGE_U0, SAFE_X_MAX))
    log('  src = %s' % rel(src))
    log('=' * 92)
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    code2ch = {int(v): k for k, v in cs['codes'].items()}
    occ = text_occurrences(textdir)
    log('[读] charset 映射 %d 条; 正文出现次数表: %s'
        % (len(code2ch), ('%d 个字' % len(occ)) if occ else '读不到 (只影响 live 标注)'))

    M = load(src)
    n_used_slots = sum(1 for _c, (b1, b2) in cs['pair_of'].items()
                       if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI)
    log('[读] 图集 %dx%d psm=0x%02X 墨 %d px; 3 个 face 记录 %s'
        % (W, H, M['ad']['psm'], int(M['ink'].sum()),
           '/'.join('%s %d' % (t[0], t[3]) for t in M['tables'])))
    log('[读] charset: 对偶字 %d 个 (在用对偶格 %d 个, 槽位 %d 个), 单字节字 %d 个'
        % (len(cs['pair_of']), n_used_slots, tcslib.pair_capacity(), len(cs['codes'])))
    before_u1 = max(rc[2] for nm in FACE_ORDER for c, r in M['rec'][nm].items()
                    if (rc := rect_of(r)) is not None)
    log('[读] 改动前: 3 个 face 全部非退化记录 max(u1) = %d' % before_u1)

    moves, used, other_rects = build_plan(M, code2ch, occ, log)
    if not moves:
        log('**无改动** (幂等: 这张盘已经修过了 / 或根本没有越界记录)')
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
            log('产物 = 输入逐字节拷贝 → %s' % rel(dst))
        doc = dict(format='zh109-edge-fix/1', src=rel(src), dst=rel(dst), changed=False,
                   moves=[], note='幂等: 没有 u0 ≥ %d 的记录 ⇒ 0 改动' % EDGE_U0,
                   asserts=lines)
        os.makedirs(os.path.dirname(report), exist_ok=True)
        io.open(report, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
        print('[rep ] → %s' % rel(report))
        return 0

    log('[plan] 候选 %d 条 (全 face 合计 %d 条记录, 去重后 %d 个新矩形): '
        % (len(moves), sum(len(m['faces']) for m in moves),
           len(set(tuple(m['new']) for m in moves))))
    _seen_grp = set()
    for m in moves:
        grp = m['shared_with']
        gkey = tuple(sorted(grp + [m['code']])) if grp else None
        if gkey and gkey in _seen_grp:
            continue
        if gkey:
            _seen_grp.add(gkey)
        sh = (' ← 共用同一空矩形的一整组 (%d 条: %s)'
              % (len(grp) + 1, ' '.join('0x%02X' % c for c in sorted(grp + [m['code']])))) \
            if grp else ''
        log('   0x%02X %-2s %2dx%-2d 旧(%4d,%3d,%4d,%4d) → 新(%4d,%3d,%4d,%4d) 墨 %3d px '
            '活=%-5s 正文=%-4s faces=%-18s%s'
            % (m['code'], m['char'] or '-', m['w'], m['h'], *m['old'], *m['new'], m['ink'],
               m['live'], m['occ'] if m['occ'] is not None else '-', ','.join(m['faces']), sh))
    tgt, diff, old_mask, new_mask, protect = check_plan(M, moves, used, other_rects, log)
    ink = M['ink']
    moved_codes = set(m['code'] for m in moves)
    newmap0 = {m['code']: m['new'] for m in moves}
    after_u1 = 0
    for nm in FACE_ORDER:
        for c, r in M['rec'][nm].items():
            rc = rect_of(r)
            if rc is None:
                continue
            after_u1 = max(after_u1, newmap0[c][2] if c in moved_codes else rc[2])
    assert after_u1 <= EDGE_U0, '方案算完后 max(u1) 仍 = %d' % after_u1
    log('⑤ 搬完后: 全部非退化记录 max(u1) = %d (= 对偶网格最右列的右缘) ≤ %d ✓'
        % (after_u1, EDGE_U0))
    for m in moves:
        if m['ink'] == 0:
            continue
        u0, v0, u1, v1 = m['old']
        nu0, nv0, nu1, nv1 = m['new']
        assert np.array_equal(tgt[nv0:nv1, nu0:nu1], ink[v0:v1, u0:u1]), \
            '0x%02X 的目标图里字形没搬对' % m['code']
    log('   有墨的 %d 条: 目标图里新矩形的像素 == 旧矩形像素 (逐像素) ✓'
        % sum(1 for m in moves if m['ink']))

    if a.dry_run or not a.dst:
        log('[dry ] 未写盘 (--dry-run)')
        return 0

    # ---- 写像素 (封包感知; 48B 包头一个字节都不动) ----
    A = M['A']
    hdr_before = {doff: bytes(A.nib[doff - tcslib.ATLAS_PREFIX_BYTES:doff])
                  for (fr, doff, nb) in A.segs}
    ys, xs = np.where(diff)
    for y, x in zip(ys.tolist(), xs.tolist()):
        A.set_px(int(x), int(y), bool(tgt[y, x]), EMPTY_NIB)
    back, _cov = A.decode_engine()
    assert np.array_equal(back, tgt), '内存回读: 引擎图与目标图不一致 (%d px)' % int((back != tgt).sum())
    for (fr, doff, nb) in A.segs:
        assert bytes(A.nib[doff - tcslib.ATLAS_PREFIX_BYTES:doff]) == hdr_before[doff], \
            '48B 包头被改动 (doff=0x%X)' % doff
    log('   像素容器: %d 段 48B 包头逐字节不变 ✓; 改动全部落在段数据区 ✓' % len(A.segs))

    # ---- 写记录表 ----
    ft = bytearray(M['w']['ft_blob'])
    off_of = {nm: off for (nm, fld, off, nrec) in M['tables']}
    uv_span, n_upd = [], 0
    for m in moves:
        idx = m['code'] - 0x20
        for nm in m['faces']:
            o = off_of[nm] + idx * 10
            b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', ft, o)
            assert (u0, v0, u1, v1) == tuple(m['old']), \
                ('%s 0x%02X 盘上矩形与分析不符' % (nm, m['code']), (u0, v0, u1, v1), m['old'])
            struct.pack_into('<BB4H', ft, o, b0, b1, *m['new'])
            uv_span.append((o + 2, o + 10))          # 记录第 2..9 字节 = u0,v0,u1,v1
            assert ft[o] == M['w']['ft_blob'][o], 'rec[0] (pad) 被改了'
            assert ft[o + 1] == M['w']['ft_blob'][o + 1], 'rec[1] (advance) 被改了'
            n_upd += 1
    chg = [i for i in range(len(ft)) if ft[i] != M['w']['ft_blob'][i]]
    assert chg, 'FT 一个字节都没改?'
    assert all(any(lo <= i < hi for (lo, hi) in uv_span) for i in chg), \
        'FT 改动落在记录的 pad/advance 区'
    log('⑥ FONT.RES: 改写 %d 条记录的 u0/v0/u1/v1 (%d 字节); rec[0]/rec[1] 逐条原值 ✓; '
        '其它 %d 字节零改动 ✓' % (n_upd, len(chg), len(ft) - len(chg)))

    ft_slot = M['w']['ft_slot']
    subs = tcslib.lzo_subs(ft_slot)
    assert len(subs) == 1, 'FONT.RES 槽不是单帧 (%d 帧)' % len(subs)
    olen = subs[0][1]
    tail = ft_slot[8 + olen:]
    assert all(b == 0 for b in tail), 'FONT.RES 槽尾部不是零填充 —— 需人工确认'
    new_frame = tcslib.lzo_pack([(bytes(ft), len(ft))])
    # ★ 槽里那一帧后面是**零填充** (槽 4421 B / 旧帧 1481 B / 余 2940 B) ⇒ 只要新帧装进**槽**即可,
    #   余下补零 (尾部零填充引擎不读; 这也正是现役盘的样子)。
    assert len(new_frame) <= len(ft_slot), ('FONT.RES 重压超槽: %d > %d'
                                            % (len(new_frame), len(ft_slot)))
    new_slot = new_frame + b'\x00' * (len(ft_slot) - len(new_frame))
    assert b''.join(s[0] for s in tcslib.lzo_subs(new_slot)) == bytes(ft), 'FONT.RES 重压回环失败'
    log('   FONT.RES 重压 %d → %d B (槽 %d, 余量 %d B; 尾部补零 %d B) 回环逐字节一致 ✓'
        % (len(ft_slot) - 8 - len(tail), len(new_frame), len(ft_slot),
           len(ft_slot) - len(new_frame), len(new_slot) - len(new_frame)))

    # ---- 写盘 ----
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    pak_e, ft_e = M['w']['pak_e'], M['w']['ft_e']
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'] + M['ad']['px_off'])
        f.write(bytes(A.nib))
        f.seek(ft_e['iso_off'])
        f.write(new_slot)
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了'

    # ---- 回读自检 (重新从盘上装载) ----
    M2 = load(dst)
    ink2 = M2['ink']
    assert not (ink2 & old_mask).any(), '回读: 旧矩形还有墨 %d px' % int((ink2 & old_mask).sum())
    lost = int((ink & protect & ~ink2).sum())
    added = int((ink2 & protect & ~ink).sum())
    assert lost == 0 and added == 0, ('回读: 保护区 丢失 %d / 新增 %d' % (lost, added))
    ch2 = ink2 != ink
    assert not (ch2 & ~(old_mask | new_mask)).any(), '回读: 改动逸出 (旧 ∪ 新) 矩形'
    for m in moves:
        u0, v0, u1, v1 = m['old']
        nu0, nv0, nu1, nv1 = m['new']
        assert not ink2[v0:v1, u0:u1].any(), '回读: 0x%02X 的旧矩形没清干净' % m['code']
        assert np.array_equal(ink2[nv0:nv1, nu0:nu1], ink[v0:v1, u0:u1]), \
            '回读: 0x%02X 的像素不是逐像素相等' % m['code']
    log('⑦ 回读: 旧矩形墨 0 ✓; 新矩形与旧像素**逐像素相等** ✓; 保护区 丢失 %d / 新增 %d ✓; '
        '改动只落在 (旧 ∪ 新) ✓' % (lost, added))

    newmap = {m['code']: list(m['new']) for m in moves}
    nmv = {m['code']: set(m['faces']) for m in moves}
    for nm in FACE_ORDER:
        for c in sorted(M['rec'][nm]):
            ro, rn = M['rec'][nm][c], M2['rec'][nm][c]
            if c in newmap and nm in nmv[c]:
                assert (ro[0], ro[1]) == (rn[0], rn[1]), \
                    ('回读: %s 0x%02X 的 pad/advance 变了' % (nm, c))
                assert list(rn[2:6]) == newmap[c], ('回读: %s 0x%02X 的 u/v 不是新矩形' % (nm, c))
            else:
                assert ro == rn, ('回读: %s 0x%02X 不该改却被改了' % (nm, c))
    log('⑧ 回读: 被搬的 %d 条 u/v = 新矩形 ✓, pad/advance 原值 ✓, 其余记录逐字节不变 ✓' % n_upd)
    after2 = max(rc[2] for nm in FACE_ORDER for c, r in M2['rec'][nm].items()
                 if (rc := rect_of(r)) is not None)
    assert after2 <= EDGE_U0, '回读: max(u1) = %d 仍越过 %d' % (after2, EDGE_U0)
    log('⑨ 回读: 3 个 face 全部非退化记录 max(u1) = %d ≤ %d ✓' % (after2, EDGE_U0))

    # 容器外零改动
    with open(dst, 'rb') as f:
        f.seek(pak_e['iso_off'])
        pak2 = f.read(pak_e['stored'])
        f.seek(ft_e['iso_off'])
        slot2 = f.read(ft_e['stored'])
    pak1 = M['ad']['pak']
    px0, px1 = M['ad']['px_off'], M['ad']['px_off'] + len(A.nib)
    assert bytes(pak2[:px0]) == bytes(pak1[:px0]), 'COMMON.PAK: 像素容器之前的字节被改了'
    assert bytes(pak2[px1:]) == bytes(pak1[px1:]), 'COMMON.PAK: 像素容器之后的字节被改了'
    assert slot2 == new_slot, 'FONT.RES 槽回读不一致'
    log('⑩ 回读: COMMON.PAK 像素容器外零改动 ✓; FONT.RES 槽 = 预期值 ✓')

    doc = dict(format='zh109-edge-fix/1', src=rel(src), dst=rel(dst), changed=True,
               textdir=(rel(textdir) if occ else None),
               premise=dict(safe_x_max=SAFE_X_MAX, safe_u1_max=EDGE_U0, band_y=list(BAND_Y),
                            formula='引擎对偶网格 col = slot % 62 ≤ 61 ⇒ x = 16*col ≤ 976 (u1 ≤ 992)',
                            max_u1_before=before_u1, max_u1_after=after2,
                            evidence=['round54 的 64 列布局 x=0,16,...,1008',
                                      'GR_ZH98 (搬字前) 全 face max(u1)=992',
                                      '0xEC 选 (976,195,992,211) 实机正常 / 0xEE 个 (1008,195,1024,211) 斜纹方块']),
               counts=dict(moves=len(moves), records_updated=n_upd,
                           inked_moves=sum(1 for m in moves if m['ink']),
                           ink_px=sum(m['ink'] for m in moves),
                           pixels_changed=int(diff.sum()),
                           ft_bytes_changed=len(chg),
                           cleared_px=int(old_mask.sum()), written_px=int(new_mask.sum())),
               asserts=lines,
               moves=[dict(code='0x%02X' % m['code'], char=m['char'], w=m['w'], h=m['h'],
                           old=m['old'], new=m['new'], ink=m['ink'], live=m['live'], occ=m['occ'],
                           faces=m['faces'], shared_with=['0x%02X' % c for c in m['shared_with']])
                      for m in moves])
    os.makedirs(os.path.dirname(report), exist_ok=True)
    io.open(report, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('[iso ] → %s' % rel(dst))
    print('[rep ] → %s' % rel(report))
    return 0


if __name__ == '__main__':
    sys.exit(main())
