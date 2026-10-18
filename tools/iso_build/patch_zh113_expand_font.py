# -*- coding: utf-8 -*-
r"""patch_zh113_expand_font.py — round67: **字库扩容 329 字** (1175 → 1504, 把引擎容量用满)。

## 做什么

把 329 个**新汉字**的字形写进现役盘图集里那 329 个**已经空着**的引擎格里,
并把它们的对偶码加进 charset JSON。**只增不改**:

  · 现有 1175 个字的字形/格位/FT 记录 —— **一个字节都不动**;
  · `FONT.RES` (FT 记录表) —— **逐字节不变** (对偶码索引 ≥ 224 = nrec ⇒ 永远不走记录表);
  · `COMMON.PAK` 里除 `new_font_revised` 的**像素容器数据区**外 —— 逐字节不变;
  · ISO 尺寸、LBA、IMG 条目表 —— 不变。

## 为什么可以这么干 (round65 探针实机证明, 见 docs/REPORT_probe_lead_limit.md)

引擎 lead 判据 = `0xA1 ≤ b < 0xB1` (elf 4 处 `sltiu reg,0xB1`) ⇒ 对偶可寻址
`16 lead × 94 trail = 1504` 格。现役用了 1175 (slot 0..1174) ⇒ **空着 slot 1175..1503**:

    lead 0xAD trail 0xD0..0xFE = 47 格 (slot 1175..1221)
    lead 0xAE / 0xAF / 0xB0 各 94 格 (slot 1222..1503)

这 329 格经**逐格实测** = 零墨 + 不被任何 FT 记录矩形覆盖 (round65 §5.2/§5.3 + 本轮
`work/builds/GR_ZH98/temp/r67/r1_verify.py` 独立复核) ⇒ **直接可写**。

## 引擎格位公式 (无相位; 与 ELF cctc cave 一致)

    slot = (lead-0xA1)*94 + (trail-0xA1)
    row, col = slot // 62, slot % 62
    引擎格左上角 = (16*col, 2 + 16*(row + 3*[row >= 12]))
    像素容器是 GIF 封包流 (8 段 × 48B 包头) ⇒ 引擎 (x,y) → 段内偏移见 Atlas.set_px

## 字形来源 (与现役 1175 个同一条管线)

`third_party/fonts/方正像素16.ttf` 16px, 绘制原点 (8,8), 取 canvas[8:24, 8:24], 阈值 <128
—— 与 `tools/font_pipeline/gen_font16.py::render16()` /
`tools/iso_build/single_cell_font.py::Templates.get()` **逐字同款**, 故
`single_cell_font.py` 会把新格判成 `match` (diff_px == 0)。

## 写盘前硬断言 (任一不过 ⇒ 不写盘)

  ① 目标格**零墨** 且 **不被任何 FT 记录矩形 (3 个 face) 覆盖**;
  ② 目标格右缘 `x+16 < 1024` (实测最大 992) 且底缘 `y+16 ≤ 512` (实测最大 450);
  ③ 实际改动像素集合 ⊆ 329 个目标格的并集 (**不碰公式永不采样的区域**);
  ④ 329 个目标格两两不重叠, 也不与现役 1175 个已用格重叠;
  ⑤ 写入后逐格回读 == 16px 模板 (逐像素);
  ⑥ 4bpp 容器回环解出的引擎图 == 目标图; 且 PAK 里像素容器以外的字节、FONT.RES 整块
     —— 逐字节不变。

## 用法

    python tools/iso_build/patch_zh113_expand_font.py <src.iso> <dst.iso> [--dry-run]
                                                       [--no-charset] [--selection <csv>]

默认选字清单 = `tools/font_pipeline/data/charset_expand_zh113.csv`
(由 `work/builds/GR_ZH98/temp/r67/r2_select.py` 逐字渲染检验后产出)。
"""
import argparse
import csv
import io
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                       # noqa: E402
import tcslib                                                            # noqa: E402

W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
SLOT_LO = tcslib.pair_slot(0xAD, 0xD0)                                   # = 1175
N_NEW = 329
assert SLOT_LO == 1175 and SLOT_LO + N_NEW == 1504 == tcslib.pair_capacity()

TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
DEFAULT_SEL = os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                           'charset_expand_zh113.csv')
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r67',
                      'patch_report.json')
BACKUP = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r67',
                      'charset_compiled_zh16.before.json')


# ═══════════════════════════ 像素容器 (GIF 封包流) 读写 ═══════════════════════════

class Atlas(object):
    """`new_font_revised` 的像素容器: **引擎坐标**读写 (口径与 patch_zh94_glyph_align 同源)。"""

    def __init__(self, pak, px_off, px_size):
        self.PX = px_off
        blob = bytes(pak[px_off:px_off + px_size])
        self.segs = tcslib.atlas_container_segments(blob, W // 2)
        assert self.segs, '认不出封包分段'
        self.nib = bytearray(pak[px_off:px_off + W * H // 2])   # 4bpp 原始字节 (含包头)
        self.eng, self.cov = self.decode_engine()

    def decode_engine(self):
        """→ (引擎图 bool: True=墨, 覆盖 mask)。按封包把每段数据放到 TRXPOS 指定的行。"""
        img = np.zeros((H, W), dtype=bool)
        cov = np.zeros((H, W), dtype=bool)
        for first_row, doff, nbytes in self.segs:
            nrow = min(nbytes // (W // 2), H - first_row)
            if nrow <= 0:
                continue
            a = np.frombuffer(bytes(self.nib[doff:doff + nrow * (W // 2)]),
                              dtype=np.uint8).reshape(nrow, W // 2)
            img[first_row:first_row + nrow, 0::2] = (a & 0x0F) == 0
            img[first_row:first_row + nrow, 1::2] = (a >> 4) == 0
            cov[first_row:first_row + nrow, :] = True
        return img, cov

    def set_px(self, x, y, ink, empty):
        """单像素写: 引擎像素 (x,y) → 容器字节 + 半字节。"""
        k = y // tcslib.ATLAS_SEG_ROWS
        assert 0 <= k < len(self.segs), (x, y)
        first_row, doff, nbytes = self.segs[k]
        rel = (y - first_row) * (W // 2) + x // 2
        assert 0 <= rel < nbytes, ('像素不在任何段的数据区', x, y)
        off = doff + rel
        cur = self.nib[off]
        v = 0 if ink else empty
        self.nib[off] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)


# ═══════════════════════════ 16px 模板 (与 gen_font16.render16 同款) ═══════════════════════════

def make_renderer():
    from PIL import Image, ImageDraw, ImageFont
    assert os.path.isfile(TTF), TTF
    fnt = ImageFont.truetype(TTF, 16)

    def render16(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        full = a < 128
        if full.any():
            ys, xs = np.where(full)
            assert ys.min() >= 8 and xs.min() >= 8 and ys.max() < 24 and xs.max() < 24, \
                '字形 %r 墨越出 16x16 em 窗 (x %d..%d y %d..%d)' \
                % (ch, xs.min() - 8, xs.max() - 8, ys.min() - 8, ys.max() - 8)
        return win

    return render16


# ═══════════════════════════ 主流程 ═══════════════════════════

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--selection', default=DEFAULT_SEL)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-charset', action='store_true')
    a = ap.parse_args(argv)
    src, dst = a.src, a.dst
    if not a.dry_run:
        assert dst, '需要 <dst.iso> (或用 --dry-run)'

    print('=' * 78)
    print('GR_ZH113 字库扩容补丁: 1175 → 1504 对偶汉字 (用满引擎 16 lead × 94 trail)')
    print('  src = %s' % src)
    print('  dst = %s' % (dst or '(dry-run)'))
    print('=' * 78)

    # ---------- 0) 选字清单 ----------
    sel = []
    with io.open(a.selection, encoding='utf-8', newline='') as fh:
        for r in csv.DictReader(fh):
            sel.append(dict(ch=r['char'], cp=r['codepoint'], count=int(r['count']),
                            in_entries=int(r['in_entries']), slot=int(r['slot']),
                            lead=int(r['new_lead'], 16), trail=int(r['new_trail'], 16)))
    assert len(sel) == N_NEW, len(sel)
    assert [c['slot'] for c in sel] == list(range(SLOT_LO, SLOT_LO + N_NEW))
    assert len({c['ch'] for c in sel}) == N_NEW, '清单里有重复字'
    for c in sel:
        assert tcslib.pair_slot(c['lead'], c['trail']) == c['slot'], c
        assert tcslib.PAIR_LEAD_LO <= c['lead'] < tcslib.PAIR_LEAD_HI, c
        assert tcslib.PAIR_TRAIL_LO <= c['trail'] <= tcslib.PAIR_TRAIL_HI, c
    print('[sel] %d 个字: slot %d..%d, lead %s'
          % (len(sel), sel[0]['slot'], sel[-1]['slot'],
             sorted({hex(c['lead']) for c in sel})))

    # ---------- 1) 读盘 ----------
    iso = tcslib.Iso(src)
    ft_e = pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'FONT.RES':
            ft_e = e
        elif e['name'] == 'COMMON.PAK':
            pak_e = e
        if ft_e and pak_e:
            break
    assert ft_e and pak_e, '基盘里找不到 COMMON.PAK / FONT.RES'
    ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])
    ft_blob_src = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
    _he, faces = tcslib.parse_ft_faces(ft_blob_src)
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    iso.close()
    recs = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised']
    assert len(recs) == 1, 'COMMON.PAK 里 new_font_revised 记录数 = %d' % len(recs)
    _nm, psm, aw, ah, _clut, px_size, PX = recs[0]
    assert (psm, aw, ah) == (0x14, W, H), (hex(psm), aw, ah)
    print('[pak] new_font_revised @PAK+0x%X psm=0x%02X %dx%d px_size=0x%X (%.1f MB ISO)'
          % (PX, psm, aw, ah, px_size, os.path.getsize(src) / 1e9))

    A = Atlas(pak, PX, px_size)
    eng_src = A.eng.copy()
    print('[cnt] 像素容器 %d 段; 引擎图覆盖 %d/%d texel; 墨 %d texel'
          % (len(A.segs), int(A.cov.sum()), W * H, int(eng_src.sum())))

    # ---------- 2) FT 记录矩形 + 现役 charset ----------
    rect = np.zeros((H, W), dtype=bool)
    nrec = 0
    for (_nm, _fld, rs) in faces:
        for r in rs:
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 > u0 and v1 > v0:
                nrec += 1
                rect[max(0, v0):min(H, v1), max(0, u0):min(W, u1)] = True
    print('[ft  ] %d 个 face, 非空记录 %d 条 ⇒ 记录矩形覆盖 %d texel'
          % (len(faces), nrec, int(rect.sum())))

    cs = json.load(io.open(tcslib.CHARSET, encoding='utf-8'))
    pair_of = cs['pair_of']
    mine = {c['ch']: [c['lead'], c['trail']] for c in sel}
    # ★ 幂等: 允许两种输入态 —— 未扩过 (1175) 或**本补丁已经跑过** (1504, 且新增 329 条与本清单一致)
    n_before = len(pair_of)
    assert n_before in (1175, 1504), 'charset 对偶条数 = %d (既不是 1175 也不是 1504)' % n_before
    if n_before == 1504:
        for ch, v in mine.items():
            assert pair_of.get(ch) == v, \
                'charset 已是 1504 但 %r 的码位 (%s) 与本清单不符 ⇒ 不是本补丁的产物' \
                % (ch, pair_of.get(ch))
        print('[json] charset 已是 1504 且新增 329 条逐条吻合 ⇒ **幂等重跑**')
    have = set(pair_of) | set(cs['codes'])
    dup = [c['ch'] for c in sel if c['ch'] in have and pair_of.get(c['ch']) != mine[c['ch']]]
    assert not dup, '清单里有字已在 charset 且码位不同: %s' % dup
    # 本轮只增不改 ⇒ 现役 slot 必须**恰好**是 0..1174 (不含我们自己的 329 格)
    used = {tcslib.pair_slot(v[0], v[1]): ch for ch, v in pair_of.items()}
    prior_used = {s: ch for s, ch in used.items() if s < SLOT_LO}
    assert sorted(prior_used) == list(range(1175)), \
        (min(prior_used), max(prior_used), len(prior_used))
    assert set(used) == set(prior_used) | set(range(SLOT_LO, SLOT_LO + N_NEW)), \
        'charset 里有 slot ≥ %d 但不属于本清单的条目' % SLOT_LO
    print('[json] charset 对偶 %d 条 (现役 %d 条占 slot 0..1174) + 单字节 %d; 新增 %d 个字'
          % (n_before, len(prior_used), len(cs['codes']), len(sel)))
    if tcslib.ATLAS_ENGINE_SINGLE_CELLS:
        print('[warn] tcslib.ATLAS_ENGINE_SINGLE_CELLS 非空 (%d 条) —— 本轮已按**实际像素**判定, '
              '不引用该表; 若那 51 条标注没修 (round67 已证全部过期) 请一并订正'
              % len(tcslib.ATLAS_ENGINE_SINGLE_CELLS))

    # ---------- 3) ★ 硬断言 ① ② ④ ----------
    print('\n──── 写盘前硬断言 ────')
    cells = []
    for c in sel:
        slot, x, y = c['slot'], *tcslib.atlas_cell_xy_engine_view(c['slot'])
        c['x'], c['y'] = x, y
        c['row'], c['col'] = slot // NCOL, slot % NCOL
        # ① 零墨 + 无记录矩形
        n_ink = int(eng_src[y:y + CH, x:x + CW].sum())
        n_rec = int(rect[y:y + CH, x:x + CW].sum())
        assert n_ink == 0, '① slot=%d (%s) 目标格有 %d 个墨点 —— 会覆盖活字形!' % (slot, c['ch'], n_ink)
        assert n_rec == 0, '① slot=%d (%s) 目标格被 %d 个 FT 记录矩形像素压着!' % (slot, c['ch'], n_rec)
        # ② 不压右缘 / 不越底缘 / 在覆盖区内
        assert x + CW < W, '② slot=%d x+16=%d 压到贴图右缘!' % (slot, x + CW)
        assert y + CH <= H, '② slot=%d y+16=%d 越出贴图底缘!' % (slot, y + CH)
        assert A.cov[y:y + CH, x:x + CW].all(), '② slot=%d 格里有容器未覆盖的 texel' % slot
        cells.append((x, y))
    print('① 329 格**零墨** 且 **无 FT 记录矩形** ✓  (逐格实测, 不看任何静态标注表)')
    print('② 右缘 max x+16 = %d < %d ✓ ; 底缘 max y+16 = %d ≤ %d ✓ ; 全格在容器覆盖区内 ✓'
          % (max(x for x, _ in cells) + CW, W, max(y for _, y in cells) + CH, H))

    # ④ 目标格两两不重叠 + 与现役已用格不重叠
    target = np.zeros((H, W), dtype=bool)
    for (x, y) in cells:
        blk = target[y:y + CH, x:x + CW]
        assert not blk.any(), '④ 目标格 (%d,%d) 与另一个目标格重叠' % (x, y)
        blk[:] = True
    live = np.zeros((H, W), dtype=bool)
    for slot in prior_used:
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        live[y:y + CH, x:x + CW] = True
    assert not (target & live).any(), \
        '④ 目标格与现役 %d 个已用格重叠 %d px' % (len(prior_used), int((target & live).sum()))
    print('④ 329 格互不重叠 ✓ 且与现役 %d 个已用格**零重叠** ✓' % len(prior_used))

    # ---------- 4) 渲染 + 写进引擎图副本 ----------
    render16 = make_renderer()
    empty_val = 1
    tpl = {}
    for c in sel:
        g = render16(c['ch'])
        assert g.any(), '空字形 %r' % c['ch']
        tpl[c['ch']] = g
    # 「空」取值自检: 全体 nibble 直方图里除 0 以外最多的那个 (与 patch_zh94 同口径)
    nb = np.frombuffer(bytes(A.nib), dtype=np.uint8)
    tot = np.bincount(nb & 0x0F, minlength=16) + np.bincount(nb >> 4, minlength=16)
    tot[0] = 0
    empty_val = int(np.argmax(tot))
    assert empty_val == 1, '「空」的调色板索引 = %d (期望 1)' % empty_val
    print('[pack] 「空」= 调色板索引 %d (nibble 直方图 %s)'
          % (empty_val, ' '.join('%X:%d' % (i, tot[i]) for i in range(16))))

    tgt = eng_src.copy()
    for c in sel:
        tgt[c['y']:c['y'] + CH, c['x']:c['x'] + CW] = tpl[c['ch']]
    # ③ 改动像素 ⊆ 目标格并集 (bool 口径)
    diff = tgt != eng_src
    outside = diff & ~target
    assert not outside.any(), \
        '③ 有 %d 个改动像素落在 329 个目标格之外 (公式永不采样的区域)!' % int(outside.sum())
    n_ch = int(diff.sum())
    n_ink_tpl = int(sum(int(t.sum()) for t in tpl.values()))
    assert n_ch == n_ink_tpl, (n_ch, n_ink_tpl)      # 源格零墨 ⇒ 只有模板的墨点算"新墨"
    print('③ 新墨 %d px (= 329 个模板的墨点总数), **全部**落在 329 个目标格内 '
          '(格外的墨点改动 = %d) ✓' % (n_ch, int(outside.sum())))

    # ③b 字节级允许区: 329 格覆盖到的**全部字节偏移** (整格 256 px 都允许重写)
    def _off_of(x, y):
        k = y // tcslib.ATLAS_SEG_ROWS
        first_row, doff, nbytes = A.segs[k]
        rel = (y - first_row) * (W // 2) + x // 2
        assert 0 <= rel < nbytes, (x, y)
        return doff + rel
    allowed = set()
    for c in sel:
        for dy in range(CH):
            for dx in range(0, CW, 2):
                allowed.add(_off_of(c['x'] + dx, c['y'] + dy))
    n_allowed = len(allowed)
    assert n_allowed == N_NEW * CW * CH // 2, (n_allowed, N_NEW * CW * CH // 2)
    nib0 = bytes(A.nib)
    allowed &= {i for i in range(len(nib0)) if nib0[i] != 0}      # 只可能改"非全零"的字节
    print('   字节级允许区 = %d B (= 329 格 × 128 B), 其中非零字节 %d B'
          % (N_NEW * CW * CH // 2, len(allowed)))

    # ---------- 5) 写回容器 (逐像素, 只走 set_px, 不碰包头) ----------
    #   整格 256 px 全部重写 (不只是"与源不同的那些") ⇒ 格内 texel 恰好只有 墨(0) / 空(empty_val)
    for c in sel:
        for dy in range(CH):
            row = tpl[c['ch']][dy]
            for dx in range(CW):
                A.set_px(c['x'] + dx, c['y'] + dy, bool(row[dx]), empty_val)
    n_written = N_NEW * CW * CH
    # ③c 字节级: 真正变了的字节必须**全部**落在允许区内
    changed_off = sorted(i for i in range(len(nib0)) if nib0[i] != bytes(A.nib)[i])
    stray = [i for i in changed_off if i not in allowed]
    assert not stray, '③ 有 %d 个字节改动落在 329 个目标格之外! 前几个 0x%X' \
                      % (len(stray), stray[0])
    print('③ 字节级: 重写 %d px; 实际变动 %d B, **全部**落在允许区 %d B 内 '
          '(拾荒改动 = 0) ✓' % (n_written, len(changed_off), n_allowed))

    back, _cov = A.decode_engine()
    assert (back == tgt).all(), '回环失败: 回写后引擎图与目标图不一致'
    print('[pack] 回写 %d 像素; 重新解封包核对引擎图一致 ✓' % n_written)

    # ⑤ 逐格回读 == 16px 模板
    bad = []
    for c in sel:
        blk = back[c['y']:c['y'] + CH, c['x']:c['x'] + CW]
        if not (blk == tpl[c['ch']]).all():
            bad.append((c['ch'], c['slot']))
    assert not bad, '⑤ 回读逐格比对失败: %s' % bad[:5]
    print('⑤ 329 格回读 == 16px 模板 (逐像素, diff_px=0) ✓')

    # ⑥ (写盘后回读再验; 见下)
    if a.dry_run:
        print('\n[dry ] --dry-run: 不写盘, 不改 charset。')
        return 0

    # ---------- 6) 写 ISO ----------
    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'] + PX)
        f.write(bytes(A.nib))
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了!'
    print('[iso ] → %s (尺寸不变 %d B)' % (dst, os.path.getsize(dst)))

    # 回读全盘核验: PAK 里除像素容器以外逐字节不变; FONT.RES 整块不变
    with open(dst, 'rb') as f:
        f.seek(pak_e['iso_off'])
        pak2 = f.read(pak_e['stored'])
        f.seek(ft_e['iso_off'])
        ft2 = f.read(ft_e['stored'])
    assert bytes(ft2) == bytes(ft_slot), 'FONT.RES 被动过了!'
    print('[ver ] 回读: FONT.RES %d B **逐字节不变** ✓' % len(ft2))
    assert bytes(pak2[:PX]) == bytes(pak[:PX]), '像素容器**之前**的 PAK 字节变了!'
    assert bytes(pak2[PX + W * H // 2:]) == bytes(pak[PX + W * H // 2:]), \
        '像素容器**之后**的 PAK 字节变了!'
    print('[ver ] 回读: COMMON.PAK 里除像素容器数据区外**逐字节不变** ✓')
    recs2 = [r for r in tcslib.parse_pak_records(pak2) if r[0] == 'new_font_revised']
    assert len(recs2) == 1 and recs2[0][6] == PX, recs2
    A2 = Atlas(bytearray(pak2), recs2[0][6], px_size)
    assert (A2.eng == tgt).all(), '回读引擎图 != 目标图'
    print('[ver ] 回读: 从盘上重新解出的引擎图 == 目标图 ✓')

    # ---------- 7) charset JSON (只增不改) ----------
    if not a.no_charset:
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        if not os.path.exists(BACKUP):
            shutil.copyfile(tcslib.CHARSET, BACKUP)
            print('[json] 备份原 charset → %s' % BACKUP)
        before = json.load(io.open(BACKUP, encoding='utf-8'))
        js = json.load(io.open(tcslib.CHARSET, encoding='utf-8'))
        # ★ 现役 1175 条必须与**原始备份**逐条一致 (只增不改; 幂等重跑同样成立)
        assert len(before['pair_of']) == 1175, len(before['pair_of'])
        assert len(js['pair_of']) in (1175, 1504), len(js['pair_of'])
        drift = [(ch, before['pair_of'][ch], js['pair_of'].get(ch))
                 for ch in before['pair_of'] if js['pair_of'].get(ch) != before['pair_of'][ch]]
        assert not drift, '现役 pair_of 被改动了 %d 条 (本轮要求只增不改)! 前 3: %s' \
                          % (len(drift), drift[:3])
        assert js['codes'] == before['codes'], 'codes 被改动了!'
        already = len(js['pair_of']) == 1504
        added = {}
        for c in sel:
            js['pair_of'][c['ch']] = [c['lead'], c['trail']]
            added[c['ch']] = '%02X%02X slot=%d (%d,%d)' % (c['lead'], c['trail'], c['slot'],
                                                           c['x'], c['y'])
        assert len(js['pair_of']) == 1504, len(js['pair_of'])
        js['_expand_zh113'] = dict(
            note='round67: 字库扩容 329 字 —— 用满引擎 lead 上限 (0xA1<=b<0xB1 ⇒ 16x94=1504)。'
                 '新字只占**原本就空着**的 slot 1175..1503 (lead 0xAD trail D0..FE / '
                 '0xAE / 0xAF / 0xB0); 现役 1175 个字的码位/格位/FT 记录一个字节都没动。'
                 '字形来源 = third_party/fonts/方正像素16.ttf 16px, 与 gen_font16.render16 同款。'
                 '见 docs/REPORT_expand_font_329.md',
            slots='%d..%d' % (SLOT_LO, SLOT_LO + N_NEW - 1),
            n_before=1175, n_added=N_NEW, n_after=1504,
            added=added,
            selection_csv='tools/font_pipeline/data/charset_expand_zh113.csv')
        io.open(tcslib.CHARSET, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(js, ensure_ascii=False, indent=1) + '\n')
        print('[json] charset 已更新: %s (1175 → 1504); 现役 1175 条逐条比对**未改动** ✓'
              % ('幂等重跑, 内容不变' if already else '+%d 条' % N_NEW))
        cs2 = tcslib.Charset()
        for c in sel:
            assert c['ch'] in cs2.enc_pair and c['ch'] not in cs2.enc_single, c
            assert tcslib.pair_slot(*cs2.enc_pair[c['ch']]) == c['slot'], c
            assert cs2.encode_strict(c['ch']) == bytes([c['lead'], c['trail']]), c
        print('[json] 新 charset 自检 ✓ (329 个字的 编码/槽位/格位 三者一致)')

    # ---------- 8) 报告 ----------
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    io.open(REPORT, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
        src=os.path.relpath(src, REPO), dst=os.path.relpath(dst, REPO),
        n_before=1175, n_added=N_NEW, n_after=1504,
        slot_lo=SLOT_LO, slot_hi=SLOT_LO + N_NEW - 1,
        lead_hist={hex(k): v for k, v in
                   sorted({l: sum(1 for c in sel if c['lead'] == l)
                           for l in {c['lead'] for c in sel}}.items())},
        pixels_changed=n_ch, pixels_written=n_written, bytes_changed=len(changed_off),
        bytes_allowed=len(allowed), empty_val=empty_val,
        ft_records=nrec, atlas_segments=len(A.segs),
        added=[dict(char=c['ch'], codepoint=c['cp'], count=c['count'],
                    in_entries=c['in_entries'], slot=c['slot'],
                    lead='0x%02X' % c['lead'], trail='0x%02X' % c['trail'],
                    cell=[c['x'], c['y']]) for c in sel]),
        ensure_ascii=False, indent=1) + '\n')
    print('[rep ] → %s' % REPORT)
    print('\n[OK  ] GR_ZH113 字库扩容补丁完成: 1175 → 1504 对偶汉字')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
