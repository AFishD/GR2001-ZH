# -*- coding: utf-8 -*-
r"""patch_zh104_relocate.py — round54: 把 84 条"占着对偶格"的单字节字形搬到对偶网格**之外**的空区

## 现象 (round52/53 侦察)

`font_cell_map.py` 把 1504 个对偶槽位逐个分类, 其中 **88 个**判成 `held_ft`
(「被活字形占着」)—— 那些格子里确实有墨, 而那块墨**归 84 条 FT 记录**所有:

  · 80 条单字节汉字 (0x92/0x9D..0xA0/0xB2..0xC1/0xC2..0xFE) —— 16x16 记录矩形, 正好等于一个对偶格;
  · 4 条引擎硬用的小字形: 箭头 `0x7B`/`0x7D` (5x13) 与 `ç 0xE7`/`ñ 0xF1` (7x13) —— 各压 2 格。

这 88 个格因而**当不成可用格** (可用格 234, 想写新字只能去抢别的地方)。

## 思路: 搬字, 不改字形

引擎对单字节码的采样是**纯 UV**:
  · `ComputeCharTextureCoords` 把 FT 记录的 `u0/v0/u1/v1` 原样 `/2` 当纹理坐标 (无重排);
  · 屏幕上的四边形 = `(x, y, x+advance×scaleX, y+CharHeight×scaleY)`
    (`docs/han_v2/PS2_FONT_MECHANISM.md` §2.2/§3, 反汇编 0x21ADE0 / 0x219A70)。
  ⇒ **记录矩形在图集里的绝对位置不影响显示**, 只影响"采样哪一块 texel";
    只要把**同一块像素**搬到别处、并把记录指过去, 显示逐像素不变, 而原来的格子就空出来了。

目标落点 = **对偶网格之外的空区** `y=194..241` (网格行 11 结束于 y=193, 行 12 起于 y=242;
这段 48 行**墨 0 px、无任何记录矩形**)。实测该区 192 个 16x16 干净格 ⇒ 84 条各占一格绰绰有余。

★ 落点为什么不用 `y=194`: `atlas_cell_xy_engine_view` 对**回绕列**会 `y+1` ⇒ 网格行 11 的
  16 个回绕格 (x=0..255) 覆盖 `y=179..194` ⇒ y=194 那一行属于**在用对偶格**。
  本补丁把 84 条全部放进 `y=195..210` / `y=211..226` 两条 16 行带 (仍在 194..241 内), 天然避开。

## 硬断言 (写盘前)

  ① 待清像素只落在 84 条旧矩形内; 旧矩形 ∩ 在用对偶格 = 0; 旧矩形 ∩ **别的**记录矩形 = 0;
     88 个格子的墨必须**全部**落在待清区内 (⇒ 清完格子真空白);
  ② 保护区 (1175 个在用对偶格 + 所有其它记录矩形) 与"改动像素"交集 = 0;
  ③ 新矩形全在 `y=194..241`、互相不重叠、不与任何 face 的任何记录矩形重叠、不与在用格重叠、
     写前墨 = 0; 且尺寸与旧矩形**逐条相同**;
  ④ `advance`(rec[1]) 与 `pad`(rec[0]) **一个字节都不动** —— 只改 u/v。

## 回读自检 (写盘后, 用另一份 `load_font`)

  · 84 条旧矩形: 墨 = 0;
  · 84 条新矩形: 与旧矩形的像素**逐像素相等**;
  · 保护区: 丢失 0 px / 新增 0 px;
  · 改动像素只落在 (84 旧 ∪ 84 新) 矩形内;
  · 3 个 face 的记录: 84 条的 u/v = 新矩形, rec[0]/rec[1] 原值; 其余记录**逐字节**不变;
  · 像素容器 48B 包头 8 段逐字节不变; 容器外 (COMMON.PAK 其它记录 / FONT.RES 槽外) 零改动。

## 幂等

在已经搬过的盘上再跑: 88 个"被活字形占着"的格子已经是 0 ⇒ **什么都不做**, 产物与基底逐字节相同。

## 用法

  python tools/iso_build/patch_zh104_relocate.py <src.iso> <dst.iso> [--text <文本表目录>]
                                                 [--report <json>] [--dry-run]

  ⚠ `--text` 默认 = `<src.iso 所在目录>/text` —— 判"活字形"要用正文出现次数
    (与 `font_cell_map.py` / `patch_zh103_recycle.py` 同一口径), 目录不在就必须显式给。
"""
import argparse
import csv
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

import dump_font as D                                                # noqa: E402
import tcslib                                                        # noqa: E402
from patch_zh94_glyph_align import Atlas                             # noqa: E402

CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
KEEP_HARD = {0x7B, 0x7D, 0xB1, 0xB5}      # 引擎硬编码: 滚动箭头 / 图标码 (与 font_cell_map 同口径)
W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
FREE_Y0, FREE_Y1 = 194, 242               # 允许落点 (半开区间)
BAND_Y = (195, 211)                       # 实际用的两条 16 行带 (避开 y=194 回绕行 / y=242 行 12)
EMPTY_NIB = 1                             # 现役容器的背景 nibble (= 封包填充 0x11)
FACE_ORDER = ['large', 'default', 'huge']


def rel(p):
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def face_tables(ft_blob):
    """展开态 FONT.RES → [(name, fld14, 记录表字节偏移, nrec)] (偏移是**字节**, 供原地改写)。"""
    p = 0
    l0 = struct.unpack_from('<I', ft_blob, p)[0]
    p += 4 + l0
    nf = struct.unpack_from('<I', ft_blob, p)[0]
    p += 4
    out = []
    for _ in range(nf):
        l = struct.unpack_from('<I', ft_blob, p)[0]
        nm = ft_blob[p + 4:p + 4 + l].decode('latin-1')
        p += 4 + l
        fld = list(struct.unpack_from('<14I', ft_blob, p))
        p += 56
        nrec = fld[4] * fld[5]
        out.append((nm, fld, p, nrec))
        p += nrec * 10
    return out, p


def text_occurrences(textdir):
    """正文出现次数 (判"活字形"用) —— 与 font_cell_map.py / patch_zh103_recycle.py 同一份表。"""
    occ = {}
    if not textdir or not os.path.isdir(textdir):
        raise SystemExit('!! 找不到文本表目录 %s\n'
                         '   (判"哪些单字节码是活字形"必须看正文出现次数; 用 --text 指定)'
                         % (textdir or '(未给)'))
    for fn in sorted(os.listdir(textdir)):
        if fn.endswith(('_text_long.csv', '_text_long_nowrap.csv', '_text_short.csv')):
            with io.open(os.path.join(textdir, fn), encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    for ch in (row.get('text_edited') or ''):
                        occ[ch] = occ.get(ch, 0) + 1
    if not occ:
        raise SystemExit('!! 文本表读出来是空的 (%s) —— 中止 (否则会把活字形当垃圾搬走)' % textdir)
    return occ


def analyse(iso, textdir):
    """只读分析: 图集 / 3 个 face / 88 个"被活字形占着"的格子 / 84 条占位记录。"""
    w = D.load_font(iso)
    ad, faces = w['atlas'], w['faces']
    assert (ad['w'], ad['h']) == (W, H), (ad['w'], ad['h'])
    A = Atlas(bytearray(ad['pak']), ad['px_off'], ad['px_size'])
    assert (A.eng.shape == (H, W))
    ink = A.eng
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    code2ch = {int(v): k for k, v in cs['codes'].items()}
    occ = text_occurrences(textdir)

    def is_live(code):
        if code in KEEP_HARD or 0x20 <= code <= 0x7E:
            return True
        if code in code2ch:
            return occ.get(code2ch[code], 0) > 0
        return False

    tables, ft_end = face_tables(w['ft_blob'])
    names = [t[0] for t in tables]
    assert names == FACE_ORDER, 'face 顺序变了: %s' % names
    face_rect = {}                       # face → {code: (u0,v0,u1,v1)}
    face_rec = {}                        # face → {code: (b0,b1,u0,v0,u1,v1)}
    for (nm, fld, off, nrec) in tables:
        d = {}
        for i in range(nrec):
            r = struct.unpack_from('<BB4H', w['ft_blob'], off + 10 * i)
            if r[4] > r[2] and r[5] > r[3]:
                d[i + 0x20] = r
        face_rect[nm] = {c: (r[2], r[3], r[4], r[5]) for c, r in d.items()}
        face_rec[nm] = d

    # 活矩形 (只取 large 面 —— 与 font_cell_map.py 同口径; default 面矩形实测逐条相同)
    live = np.zeros((H, W), dtype=bool)
    for c, (u0, v0, u1, v1) in face_rect['large'].items():
        if is_live(c):
            live[v0:v1, u0:u1] = True

    slot_of = {}
    for ch, (b1, b2) in cs['pair_of'].items():
        if tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI:
            slot_of[tcslib.pair_slot(b1, b2)] = ch
    used = np.zeros((H, W), dtype=bool)
    for s in slot_of:
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        if 0 <= x and x + CW <= W and 0 <= y and y + CH <= H:
            used[y:y + CH, x:x + CW] = True

    # 88 个"被活字形占着"的格子 (判据同 font_cell_map): 格内有墨 且 该墨全在活矩形里
    held = {}
    for slot in range(1504):
        if slot in slot_of:
            continue
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        if not (0 <= x and x + CW <= W and 0 <= y and y + CH <= H):
            continue
        cell = ink[y:y + CH, x:x + CW]
        n = int(cell.sum())
        if n == 0:
            continue
        if int((cell & live[y:y + CH, x:x + CW]).sum()) != n:
            continue
        held[slot] = (x, y, n)

    # 每个格子的归属 (跨 3 个 face 的记录矩形)
    all_rect = {}                        # (face, code) → rect
    for nm in FACE_ORDER:
        for c, r in face_rect[nm].items():
            all_rect[(nm, c)] = r
    owners = {}
    for slot, (x, y, n) in held.items():
        hits = sorted(set(c for (nm, c), r in all_rect.items()
                          if x < r[2] and x + CW > r[0] and y < r[3] and y + CH > r[1]))
        owners[slot] = hits
    return dict(w=w, ad=ad, A=A, ink=ink, cs=cs, code2ch=code2ch, occ=occ, is_live=is_live,
                tables=tables, ft_end=ft_end, face_rect=face_rect, face_rec=face_rec,
                live=live, used=used, slot_of=slot_of, held=held, owners=owners,
                textdir=textdir)


def build_plan(M):
    """84 条占位记录 → (旧矩形, 新矩形) 方案; 不做任何写盘。"""
    held, owners, face_rect = M['held'], M['owners'], M['face_rect']
    ink = M['ink']
    bad = {s: o for s, o in owners.items() if len(o) != 1}
    assert not bad, '这些格被多条记录压着 (不能整条搬): %s' % list(bad.items())[:5]
    codes = sorted(set(o[0] for o in owners.values()))
    moves = []
    for c in codes:
        rects = {}
        for nm in FACE_ORDER:
            r = face_rect[nm].get(c)
            if r is not None:
                rects[nm] = r
        uniq = set(rects.values())
        assert len(uniq) == 1, ('0x%02X 在不同 face 里的矩形不一样, 需要逐 face 处理: %s'
                                % (c, rects))
        u0, v0, u1, v1 = rects['large']
        assert u1 > u0 and v1 > v0, (c, rects)
        moves.append(dict(code=c, w=u1 - u0, h=v1 - v0, old=[u0, v0, u1, v1],
                          faces={nm: list(r) for nm, r in rects.items()},
                          cells=sorted(s for s, o in owners.items() if o[0] == c)))
    # 布局: 大的先排 (16x16 每条一格), 小的排后面; 两条 16 行带, x = 16*k
    big = [m for m in moves if (m['w'], m['h']) == (CW, CH)]
    small = [m for m in moves if (m['w'], m['h']) != (CW, CH)]
    # round59 硬化: 列数**不许用 W//CW(=64)** —— 对偶网格只用 col=slot%62<=61 ⇒ x<=976;
    # x=1008 时 x+16=1024=贴图宽度 ⇒ 引擎取样取不到, 实机渲染成乱码
    # (原版 64 列布局把「个」0xEE 停到 x=1008, 训练7 教程页出现斜纹方块;
    #  见 docs/REPORT_edge_fix_zh109.md / tools/iso_build/patch_zh109_edge_fix.py)
    cells = [(y0, CW * k) for y0 in BAND_Y for k in range(min(W // CW, NCOL))]
    assert len(big) + len(small) <= len(cells), (len(big), len(small), len(cells))
    for m, (y0, x0) in zip(big + small, cells):
        m['new'] = [x0, y0, x0 + m['w'], y0 + m['h']]
        m['char'] = M['code2ch'].get(m['code'], {0x7B: '{', 0x7D: '}', 0xE7: 'ç',
                                                 0xF1: 'ñ'}.get(m['code'], '?'))
        m['ink'] = int(ink[m['old'][1]:m['old'][3], m['old'][0]:m['old'][2]].sum())
    return moves


def mask_of(rects):
    m = np.zeros((H, W), dtype=bool)
    for (u0, v0, u1, v1) in rects:
        m[v0:v1, u0:u1] = True
    return m


def check_plan(M, moves, log):
    """写盘前的硬断言 (① ② ③)。"""
    ink, used = M['ink'], M['used']
    old_mask = mask_of([tuple(m['old']) for m in moves])
    move_codes = set(m['code'] for m in moves)

    # ① 待清像素的干净性
    assert not (old_mask & used).any(), '待清像素落在**在用对偶格**里'
    other = np.zeros((H, W), dtype=bool)
    for nm in FACE_ORDER:
        for c, (u0, v0, u1, v1) in M['face_rect'][nm].items():
            if c in move_codes:
                continue
            other[v0:v1, u0:u1] = True
    assert not (old_mask & other).any(), '待清像素落在**别的记录矩形**里'
    for slot, (x, y, n) in M['held'].items():
        cell = ink[y:y + CH, x:x + CW]
        assert not (cell & ~old_mask[y:y + CH, x:x + CW]).any(), \
            'slot %d 的墨有 %d px 不在待清区里 (清不干净)' % (slot, int((cell & ~old_mask[y:y + CH, x:x + CW]).sum()))

    # ③ 新矩形
    new_mask = mask_of([tuple(m['new']) for m in moves])
    assert int((new_mask & old_mask).sum()) == 0, '新/旧矩形重叠'
    for m in moves:
        u0, v0, u1, v1 = m['new']
        assert FREE_Y0 <= v0 and v1 <= FREE_Y1, ('新矩形出空区', m['code'], m['new'])
        assert (u1 - u0, v1 - v0) == (m['w'], m['h']), ('尺寸变了', m['code'])
        assert int(ink[v0:v1, u0:u1].sum()) == 0, ('新矩形写前不是空的', m['code'])
    assert not (new_mask & used).any(), '新矩形压在**在用对偶格**上'
    assert not (new_mask & other).any(), '新矩形压在**别的记录矩形**上'
    assert not (new_mask & old_mask).any(), '新矩形压在旧矩形上'
    cnt = np.zeros((H, W), dtype=np.uint8)
    for m in moves:
        u0, v0, u1, v1 = m['new']
        cnt[v0:v1, u0:u1] += 1
    assert cnt.max() <= 1, '新矩形互相重叠 (%d 处)' % int((cnt > 1).sum())

    # ② 保护区 = 在用格 ∪ 别的记录矩形 (与改动像素交集必须 0)
    protect = used | other
    assert not ((old_mask | new_mask) & protect).any(), '改动像素侵入保护区'
    log('① 待清 %d px (84 旧矩形) ∩ 在用格 0 ✓ ∩ 别的记录矩形 0 ✓; 88 格的墨全部落在待清区 ✓'
        % int(old_mask.sum()))
    log('② 保护区 = 在用对偶格 %d 个 (%d px) ∪ 别的记录矩形 (%d px) —— 与改动像素交集 0 ✓'
        % (len(M['slot_of']), int(used.sum()), int(other.sum())))
    log('③ 新矩形 %d 个: 全在 y=%d..%d ✓ 互不重叠 ✓ 尺寸逐条不变 ✓ 写前墨 0 ✓ '
        '∩ 在用格 0 ✓ ∩ 别的记录矩形 0 ✓'
        % (len(moves), FREE_Y0, FREE_Y1 - 1))
    return protect, old_mask, new_mask


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--text', default=None, help='文本表目录 (判"活字形"用; 默认 <src目录>/text)')
    ap.add_argument('--report', default=None)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    src = a.src
    dst = a.dst or src
    textdir = a.text or os.path.join(os.path.dirname(os.path.abspath(src)), 'text')
    report = a.report or os.path.join(os.path.dirname(os.path.abspath(dst)),
                                      os.path.splitext(os.path.basename(dst))[0]
                                      + '_relocate_report.json')
    lines = []

    def log(s):
        print(s)
        lines.append(s)

    print('=' * 78)
    print('GR_ZH104 搬运补丁: 88 个"被活字形占着"的对偶格 → 腾空 (84 条记录改指对偶网格外空区)')
    print('  src = %s' % rel(src))
    print('  text= %s' % rel(textdir))
    print('=' * 78)
    M = analyse(src, textdir)
    log('基盘: 图集 %dx%d 墨 %d px; 在用对偶格 %d 个; 判活口径 = charset + 正文出现次数'
        % (W, H, int(M['ink'].sum()), len(M['slot_of'])))

    if not M['held']:
        log('88 个"被活字形占着"的格子 = 0 ⇒ **无改动** (幂等: 这张盘已经搬过了)')
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)
            log('产物 = 基底逐字节拷贝 → %s' % rel(dst))
        io.open(report, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(dict(src=rel(src), dst=rel(dst), changed=False, held_cells=0,
                            moves=[], note='幂等: 没有"被活字形占着"的格子 ⇒ 0 改动'),
                       ensure_ascii=False, indent=1) + '\n')
        print('[rep ] → %s' % rel(report))
        return 0

    log('88 格实测 = **%d 个** "被活字形占着" (压着它们的记录去重后 %d 条)'
        % (len(M['held']), len(set(o[0] for o in M['owners'].values()))))
    moves = build_plan(M)
    log('占位记录 %d 条 (16x16 汉字 %d 条 + 小矩形 %d 条); 待搬墨 %d px'
        % (len(moves), sum(1 for m in moves if (m['w'], m['h']) == (CW, CH)),
           sum(1 for m in moves if (m['w'], m['h']) != (CW, CH)),
           sum(m['ink'] for m in moves)))
    for m in moves:
        if (m['w'], m['h']) != (CW, CH):
            log('   小矩形 0x%02X %s %dx%d 旧 %s → 新 %s (压 %d 格)'
                % (m['code'], m['char'], m['w'], m['h'], m['old'], m['new'], len(m['cells'])))
    protect, old_mask, new_mask = check_plan(M, moves, log)

    # ---- 目标图 ----
    A, ink = M['A'], M['ink']
    tgt = ink.copy()
    for m in moves:
        u0, v0, u1, v1 = m['old']
        nu0, nv0, nu1, nv1 = m['new']
        tgt[nv0:nv1, nu0:nu1] = ink[v0:v1, u0:u1]
        tgt[v0:v1, u0:u1] = False
    diff = tgt != ink
    ys, xs = np.where(diff)
    assert not (diff & protect).any(), '待写像素侵入保护区'
    log('④ 待写像素 %d px (清 %d + 写 %d); 全部落在 84 旧 ∪ 84 新 矩形内 ✓'
        % (len(ys), int((old_mask & diff).sum()), int((new_mask & diff).sum())))
    if a.dry_run or not a.dst:
        log('[dry ] 未写盘 (--dry-run)')
        return 0

    # ---- 像素 (封包感知写; 48B 包头一个字节都不动) ----
    hdr_before = {doff: bytes(A.nib[doff - tcslib.ATLAS_PREFIX_BYTES:doff]) for (fr, doff, nb)
                  in A.segs}
    for y, x in zip(ys.tolist(), xs.tolist()):
        A.set_px(int(x), int(y), bool(tgt[y, x]), EMPTY_NIB)
    back, _cov = A.decode_engine()
    assert np.array_equal(back, tgt), '内存回读: 引擎图与目标图不一致 (%d px)' % int((back != tgt).sum())
    for (fr, doff, nb) in A.segs:
        assert bytes(A.nib[doff - tcslib.ATLAS_PREFIX_BYTES:doff]) == hdr_before[doff], \
            '48B 包头被改动 (doff=0x%X)' % doff
    log('   像素容器: 8 段 48B 包头逐字节不变 ✓; 改动落在段数据区 ✓')

    # ---- FONT.RES 记录表 ----
    ft = bytearray(M['w']['ft_blob'])
    off_of = {nm: off for (nm, fld, off, nrec) in M['tables']}
    nrec_of = {nm: nrec for (nm, fld, off, nrec) in M['tables']}
    uv_span, n_upd = [], 0
    for m in moves:
        idx = m['code'] - 0x20
        for nm in FACE_ORDER:
            if nm not in m['faces']:
                continue
            assert idx < nrec_of[nm], (nm, m['code'])
            o = off_of[nm] + idx * 10
            b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', ft, o)
            assert (u0, v0, u1, v1) == tuple(m['faces'][nm]), \
                ('%s 0x%02X 盘上矩形与分析不符' % (nm, m['code']), (u0, v0, u1, v1), m['faces'][nm])
            struct.pack_into('<BB4H', ft, o, b0, b1, m['new'][0], m['new'][1],
                             m['new'][2], m['new'][3])
            uv_span.append((o + 2, o + 10))          # 记录第 2..9 字节 = u0,v0,u1,v1
            assert ft[o] == M['w']['ft_blob'][o], 'rec[0] (pad) 被改了'
            assert ft[o + 1] == M['w']['ft_blob'][o + 1], 'rec[1] (advance) 被改了'
            n_upd += 1
    # 只许改 u/v (记录第 2..9 字节) —— pad/advance 永不触碰
    chg = [i for i in range(len(ft)) if ft[i] != M['w']['ft_blob'][i]]
    assert chg, 'FT 一个字节都没改?'
    for i in chg:
        assert any(a <= i < b for (a, b) in uv_span), \
            'FT 改动落在记录的 pad/advance 区 (off=%d)' % i
    assert len(chg) >= 2 * n_upd, '改动字节数太少: %d (每条至少 v0/v1 两字节)' % len(chg)
    log('   FONT.RES: 3 个 face 共改写 %d 条记录的 u0/v0/u1/v1 (%d 字节); '
        'rec[0]/rec[1] (pad/advance) 逐条原值 ✓; 其它 %d 字节零改动 ✓'
        % (n_upd, len(chg), len(ft) - len(chg)))

    ft_slot = M['w']['ft_slot']
    subs = tcslib.lzo_subs(ft_slot)
    assert len(subs) == 1, 'FONT.RES 槽不是单帧 (%d 帧)' % len(subs)
    olen = subs[0][1]
    tail = ft_slot[8 + olen:]
    assert all(b == 0 for b in tail), 'FONT.RES 槽尾部不是零填充 —— 需人工确认'
    new_frame = tcslib.lzo_pack([(bytes(ft), len(ft))])
    new_slot = new_frame + tail
    assert len(new_slot) <= len(ft_slot), ('FONT.RES 重压超槽: %d > %d' % (len(new_slot), len(ft_slot)))
    new_slot = new_slot + b'\x00' * (len(ft_slot) - len(new_slot))
    back_ft = b''.join(s[0] for s in tcslib.lzo_subs(new_slot))
    assert back_ft == bytes(ft), 'FONT.RES 重压回环失败'
    log('   FONT.RES 重压 %d → %d B (槽 %d) 回环逐字节一致 ✓'
        % (olen, len(new_frame), len(ft_slot)))

    # ---- 写盘 ----
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copyfile(src, dst)
    pak_e = M['w']['pak_e']
    ft_e = M['w']['ft_e']
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'] + M['ad']['px_off'])
        f.write(bytes(A.nib))
        f.seek(ft_e['iso_off'])
        f.write(new_slot)
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了'

    # ---- 回读自检 (重新从盘上装载) ----
    M2 = analyse(dst, textdir)
    A2, ink2 = M2['A'], M2['ink']
    assert not (ink2 & old_mask).any(), '回读: 旧矩形还有墨 %d px' % int((ink2 & old_mask).sum())
    lost = int((ink & protect & ~ink2).sum())
    added = int((ink2 & protect & ~ink).sum())
    assert lost == 0 and added == 0, ('回读: 保护区 丢失 %d / 新增 %d' % (lost, added))
    ch2 = ink2 != ink
    assert not (ch2 & ~(old_mask | new_mask)).any(), '回读: 改动逸出 84 旧 ∪ 84 新 矩形'
    for m in moves:
        u0, v0, u1, v1 = m['old']
        nu0, nv0, nu1, nv1 = m['new']
        assert not ink2[v0:v1, u0:u1].any(), '回读: 0x%02X 的旧矩形没清干净' % m['code']
        assert np.array_equal(ink2[nv0:nv1, nu0:nu1], ink[v0:v1, u0:u1]), \
            '回读: 0x%02X 的像素不是逐像素相等' % m['code']
    log('⑤ 回读: 84 条旧矩形墨 0 ✓; 84 条新矩形与旧像素**逐像素相等** ✓; '
        '保护区 丢失 %d / 新增 %d ✓; 改动只落在 84 旧 ∪ 84 新 ✓' % (lost, added))
    assert not M2['held'], '回读: 还有 %d 个格子"被活字形占着"' % len(M2['held'])
    log('⑥ 回读: "被活字形占着"的格子 %d → **0** ✓' % len(M['held']))

    for nm in FACE_ORDER:
        nmv = set(m['code'] for m in moves if nm in m['faces'])
        for c in sorted(M['face_rec'][nm]):
            ro, rn = M['face_rec'][nm][c], M2['face_rec'][nm][c]
            if c in nmv:
                assert (ro[0], ro[1]) == (rn[0], rn[1]), \
                    ('回读: %s 0x%02X 的 pad/advance 变了' % (nm, c))
                assert list(rn[2:6]) == list(dict((m['code'], m['new'])
                                                 for m in moves)[c]), \
                    ('回读: %s 0x%02X 的 u/v 不是新矩形' % (nm, c))
            else:
                assert ro == rn, ('回读: %s 0x%02X 不该改却被改了' % (nm, c))
    log('⑦ 回读: 3 个 face 的记录表 —— 84 条 u/v = 新矩形 ✓, pad/advance 原值 ✓, '
        '其余记录逐字节不变 ✓')

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
    log('⑧ 回读: COMMON.PAK 像素容器外零改动 ✓; FONT.RES 槽 = 预期值 ✓')

    doc = dict(
        src=rel(src), dst=rel(dst), changed=True, textdir=rel(textdir),
        premise=dict(held_cells_before=len(M['held']), held_cells_after=0,
                     used_slots=len(M['slot_of']), free_y=list(range(FREE_Y0, FREE_Y1)),
                     layout=dict(bands=list(BAND_Y), x_step=CW)),
        counts=dict(moves=len(moves), records_updated=n_upd, ink_px=sum(m['ink'] for m in moves),
                    cleared_px=int(old_mask.sum()), written_px=int(new_mask.sum()),
                    pixels_changed=len(ys)),
        asserts=lines,
        moves=[dict(code='0x%02X' % m['code'], char=m['char'], w=m['w'], h=m['h'],
                    old=m['old'], new=m['new'], faces=sorted(m['faces']),
                    cells=m['cells'], ink=m['ink']) for m in moves])
    os.makedirs(os.path.dirname(report), exist_ok=True)
    io.open(report, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(doc, ensure_ascii=False, indent=1) + '\n')
    print('[iso ] → %s' % rel(dst))
    print('[rep ] → %s' % rel(report))
    return 0


if __name__ == '__main__':
    sys.exit(main())
