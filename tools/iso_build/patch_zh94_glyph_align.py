# -*- coding: utf-8 -*-
r"""patch_zh94_glyph_align.py — GR_ZH94: 把 grid 行 19..24 的字形搬到**引擎真正采样**的格上。

## 为什么 (round45 查实, 见 docs/REPORT_glyph_align.md)

引擎 (现役 ELF 的 cctc cave, hook 0x21ADE0 → 0x417050) 对**对偶码**算采样窗:
    slot = (lead-0xA1)*94 + (trail-0xA1);  row = slot/62;  col = slot%62
    U0 = 16*col ;  V0 = 2 + 16*(row + 3*[row>=12])            ← **没有任何行相位**
对**单字节码**走另一条路 (同 cave: `if (slot+224) < fld[17]` → FT 记录表), 即用记录矩形
(u0,v0,u1,v1) 当采样窗 —— 已由实机截图证实 (M18 详情页里 后/向/装/有/雷/爆 全部正确)。

而像素容器是 **GIF 封包流** (每段 48B 包头 + 64 行数据, TRXPOS.y = 0/64/…/448):
    引擎图 (x,y)  ↔  flat 容器字节 = 512*y + x/2 + 48*(y//64 + 1)
⇒ 引擎列 = (flat 列 − 6×(段号+1)) mod 64 (不够减就进位到下一行)。

历史补丁写字形用的是 **flat 口径** (tcslib.ATLAS_PHI): flat 列 = (col + PHI[row]) mod 64。
行 0..18 恰好 PHI[row] = 6*(段号+1) ⇒ 与引擎格重合, 所以一直是对的;
行 19..24 的 PHI = 2 / 0 ⇒ 字形落到**别的列**上 (行 19/20 差 34 格, 行 21..24 差 40/42 格)。

## 本轮实测 (temp/r45/a5_ident + a6_locate, TTF 模板逐格辨认)

· 行 19 的 col 0..33 **被单字节码 0xDB..0xFE 的字形占着** (后放置不切命向和退装枪标使员人爆选
  这个设手随视游目前指更它有雷何上 — err=0 完美命中, 它们的 FT 记录矩形正是这些格)。
· 行 19..23 的 181 个已用对偶槽里, **151 个**的目标格是"自己行的字形/空格" ⇒ 直接搬像素即可;
  **30 个** (行 19 col 4..33: 米毫丁匣斤丹丽采坐款“”扳倍宾乔偏亨挂栓伟泛箱聚链震延普伯佐)
  的目标格被单字节码占着 ⇒ **搬像素修不了, 必须把这些字**改派到别的对偶槽 (charset 改码位,
  文本按新码位重编 —— 由 make_build --inject-csv 完成)。

## 做法 (全程在**引擎图**坐标里做, 不碰 48B 包头)

1. 行 20..24: 清掉整条引擎行带 (yrow..yrow+15) 里**不属于单字节码**的格, 再把每个槽位的字形
   按 (16*col, yrow) 写回 (行 24 的 col 0..5 / 12 是记录码的格, 跳过);
2. 行 19: 只清 col 34..61 (col 0..33 是单字节码的, 一个像素都不碰), 把改派后的 28 个字写进
   col 34..61; 另有 2 个字改派到行 20 的 col 0/1 (那两格在第 1 步里已清);
3. charset JSON: 那 30 个字改成新的对偶码 (并加一节 `_glyph_align_zh94` 说明);
4. 自检: 变更只落在 6 条带内; 记录码 (单字节) 的格一个像素没动; 每个字的字形原样落到新格。

用法:
  python tools/iso_build/patch_zh94_glyph_align.py <src.iso> <dst.iso> [--dry-run] [--no-charset]
"""
import io
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402

W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
ROWS = list(range(19, 25))
# ★ 取"当前字形"必须用**旧相位** (盘上字形现在还在老地方); tcslib.ATLAS_PHI 已经是订正后的真值,
#   所以这里写死旧值 (round41..round44 用的那张表: 行 19..23 = 2, 行 24 = 0)。
OLD_PHI = {19: 2, 20: 2, 21: 2, 22: 2, 23: 2, 24: 0}
REPORT = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r45', 'glyph_align_report.json')
BACKUP = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r45',
                      'charset_compiled_zh16.before.json')


def yrow(r):
    return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def new_phi(row):
    """引擎格 ↔ flat 格的**真**相位: 6*(段号+1) mod 64 (= 48 字节包头 = 96 texel 的累计错位)。"""
    return (6 * (min(yrow(row) // tcslib.ATLAS_SEG_ROWS, 7) + 1)) % tcslib.GRID_MOD


class Atlas:
    """COMMON.PAK → new_font_revised 的像素容器 (GIF 封包流) 读写。"""

    def __init__(self, pak, PX, px_size):
        self.PX = PX
        blob = bytes(pak[PX:PX + px_size])
        self.segs = tcslib.atlas_container_segments(blob, W // 2)
        assert self.segs, '认不出封包分段'
        self.nib = bytearray(pak[PX:PX + W * H // 2])      # 4bpp 原始字节 (含包头)
        self.eng, self.cov = self.decode_engine()

    # ---- 解码: 引擎看到的图 (按封包把每段数据放回 TRXPOS 指定的行) ----
    def decode_engine(self):
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

    # ---- 单像素写: 引擎像素 (x,y) → 容器字节 + 半字节 ----
    def set_px(self, x, y, ink, empty):
        k = y // tcslib.ATLAS_SEG_ROWS
        assert 0 <= k < len(self.segs), (x, y)
        first_row, doff, nbytes = self.segs[k]
        rel = (y - first_row) * (W // 2) + x // 2
        assert 0 <= rel < nbytes, ('像素不在任何段的数据区', x, y)
        off = doff + rel
        cur = self.nib[off]
        v = 0 if ink else empty
        self.nib[off] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)


def flat_to_engine(segs, fx, fy):
    """「整块当裸图」坐标 → 引擎图坐标 (用盘上真实分段表, 不猜)。"""
    b = fy * (W // 2) + fx // 2
    for first_row, doff, nbytes in segs:
        if doff <= b < doff + nbytes:
            rel = b - doff
            return (rel % (W // 2)) * 2, first_row + rel // (W // 2)
    return None, None


def main(src, dst, dry=False, do_charset=True):
    print('=' * 78)
    print('GR_ZH94 字形对齐补丁 (grid 行 19..24 的字形 → 引擎采样格 16*col / yrow)')
    print('  src = %s' % src)
    print('=' * 78)
    iso = tcslib.Iso(src)
    pak_e = ft_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
        elif e['name'] == 'FONT.RES':
            ft_e = e
        if pak_e and ft_e:
            break
    assert pak_e and ft_e, '基盘里找不到 COMMON.PAK / FONT.RES'
    pak = bytearray(iso.read(pak_e['iso_off'], pak_e['stored']))
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(bytes(pak)) if r[0] == 'new_font_revised']
    assert len(rec) == 1
    _nm, psm, w, h, clut, px_size, PX = rec[0]
    assert (psm, w, h) == (0x14, W, H), (psm, w, h)
    A = Atlas(pak, PX, px_size)
    print('[atlas] psm=0x%02X %dx%d px_off=0x%X 段=%d 引擎图墨=%d (覆盖 %d 行)'
          % (psm, w, h, PX, len(A.segs), int(A.eng.sum()), int(A.cov.sum() / W)))

    _he, faces = tcslib.parse_ft_faces(ft_blob)
    fi = {f[0]: f[2] for f in faces}
    recs = fi['default']
    print('[ft   ] faces=%s  (引擎用 default; 见 docs/FONT_CURRENT_STATE.md)' %
          [(f[0], len(f[2])) for f in faces])

    cs = tcslib.Charset()
    by_slot = {}
    for ch, (b1, b2) in cs.enc_pair.items():
        by_slot[tcslib.pair_slot(b1, b2)] = ch
    single = dict((int(c), ch) for ch, c in cs.enc_single.items())

    # ---------- 记录码的采样窗 (一个像素都不能动) ----------
    #   保守口径: **全部 3 个 face 的所有 FT 记录矩形**都算"别人的采样窗" —— 不只网格行上的
    #   那些大格, 还包括落在带里的**图标码**小矩形 (0x7B/0x7D/0xE7/0xF1 在 (89..135, 395..408),
    #   0xB1/0xB5/0x20 在 (136,420,146,436)) —— round45 第一版漏了它们, 清带时把它们擦掉了
    #   (实机表现为"详情页上下滚动箭头变暗"), 见 temp/r45/d1_iconrect.log。
    protect = np.zeros((H, W), dtype=bool)
    rects = []
    for fname, fld, rs in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            x0, x1 = max(0, u0), min(W, u1)
            y0, y1 = max(0, v0), min(H, v1)
            if x0 >= x1 or y0 >= y1:
                continue
            protect[y0:y1, x0:x1] = True
            rects.append((fname, idx + 0x20, u0, v0, u1, v1))
    sb_cell = {}
    for idx, r in enumerate(recs):
        _b0, _b1, u0, v0, u1, v1 = r
        if v1 <= v0 or u1 <= u0:
            continue
        code = idx + 0x20
        for rr in ROWS:
            if v0 == yrow(rr) and (u0 % CW) == 0 and u0 + CW <= W:
                sb_cell[(rr, u0 // CW)] = (code, single.get(code, '（休眠码位）'))
    print('[rec  ] FT 记录矩形 (3 个 face) 合计 %d 条, 保护像素 %d 个' % (len(rects), int(protect.sum())))
    print('[rec  ] 其中落在 6 条行带里的: %d 条'
          % sum(1 for _f, _c, u0, v0, u1, v1 in rects
                if any(yrow(r) < v1 and yrow(r) + CH > v0 for r in ROWS)))

    def blocked(row, col):
        """目标格 (16*col, yrow) 是否与任何记录矩形相交 (相交就不能给对偶码用)。"""
        y0 = yrow(row)
        return bool(protect[y0:y0 + CH, col * CW:(col + 1) * CW].any())

    # ---------- 行 19..24 里"目标格被记录码占着"的已用槽 → 改派 ----------
    conflict = []
    for row in ROWS:
        if yrow(row) + CH > H:
            continue
        for col in range(NCOL):
            slot = row * NCOL + col
            if slot in by_slot and blocked(row, col):
                conflict.append((row, col, by_slot[slot]))
    print()
    print('[冲突] 目标格与记录矩形相交的已用对偶槽: %d 个' % len(conflict))
    for r, c, ch in conflict:
        print('        %s (row%d col%d) ← 格 (%d,%d) 被记录矩形压着'
              % (ch, r, c, CW * c, yrow(r)))
    free = []
    for row in ROWS:
        if yrow(row) + CH > H:
            continue
        for col in range(NCOL):
            slot = row * NCOL + col
            if slot in by_slot or blocked(row, col):
                continue
            free.append((row, col))
    free.sort(key=lambda rc: (rc[0], rc[1]))
    assert len(free) >= len(conflict), '空闲槽不够: 需 %d 有 %d' % (len(conflict), len(free))
    moves = []
    for (orow, ocol, ch), (nrow, ncol) in zip(conflict, free):
        moves.append(dict(char=ch, old_slot=orow * NCOL + ocol, old_row=orow, old_col=ocol,
                          new_slot=nrow * NCOL + ncol, new_row=nrow, new_col=ncol))
    print('[改派] %s' % '; '.join('%s %d,%d→%d,%d' % (m['char'], m['old_row'], m['old_col'],
                                                       m['new_row'], m['new_col']) for m in moves))

    # ---------- 取"当前字形" (按**旧** flat 口径换算成引擎位置再取) ----------
    glyphs, nink = {}, 0
    for row in ROWS:
        if yrow(row) + CH > H:
            continue
        ph = OLD_PHI[row]
        for col in range(NCOL):
            p = col + ph
            fx, fy = CW * (p % tcslib.GRID_MOD), yrow(row) + (1 if p >= tcslib.GRID_MOD else 0)
            ex, ey = flat_to_engine(A.segs, fx, fy)
            if ex is None or ey < 0 or ey + CH > H or ex + CW > W:
                glyphs[(row, col)] = None
                continue
            g = A.eng[ey:ey + CH, ex:ex + CW].copy()
            glyphs[(row, col)] = g
            nink += int(g.any())
    print('[glyph] 取出旧字形 %d 个 (其中有墨 %d)' % (len(glyphs), nink))

    # ---------- 构造目标引擎图 ----------
    En = A.eng.copy()
    for row in ROWS:                                   # ① 清掉 6 条行带
        if yrow(row) + CH > H:
            continue
        En[yrow(row):yrow(row) + CH, :] = False
    En[protect] = A.eng[protect]                       # ② 把"别人的采样窗"原样贴回 (图标码等)
    placed, skipped = [], []
    for row in ROWS:                                   # ③ 每个槽位写回自己的格
        if yrow(row) + CH > H:
            continue
        for col in range(NCOL):
            g = glyphs.get((row, col))
            if g is None:
                continue
            y0, x0 = yrow(row), col * CW
            En[y0:y0 + CH, x0:x0 + CW] = g
            if blocked(row, col):
                skipped.append((row, col))
            else:
                placed.append((row, col, int(g.sum())))
    En[protect] = A.eng[protect]                       # ④ 保护像素最终说了算
    for m in moves:                                    # ⑤ 改派的字写到新格 (新格一定是干净的)
        g = glyphs[(m['old_row'], m['old_col'])]
        assert g is not None, m
        assert not blocked(m['new_row'], m['new_col']), m
        En[yrow(m['new_row']):yrow(m['new_row']) + CH,
           m['new_col'] * CW:(m['new_col'] + 1) * CW] = g
        m['ink'] = int(g.sum())
    print('[img  ] 写回 %d 个槽位 (其中 %d 个格子被记录矩形压着 ⇒ 只写没被压的像素), 改派 %d 个'
          % (len(placed) + len(skipped), len(skipped), len(moves)))

    # ---------- 自检 1: 变更只在 6 条带内 ----------
    diff = (En != A.eng)
    inband = np.zeros(H, dtype=bool)
    for row in ROWS:
        if yrow(row) + CH <= H:
            inband[yrow(row):yrow(row) + CH] = True
    outside = int((diff & ~inband[:, None]).sum())
    print()
    print('[self1] 引擎图变更 %d 像素; 带内 %d; 带外 %d (期望 0)'
          % (int(diff.sum()), int((diff & inband[:, None]).sum()), outside))
    assert outside == 0, '有像素改在 6 条带之外'

    # ---------- 自检 2: 记录矩形的像素一个都没变 ----------
    bad_px = int((En[protect] != A.eng[protect]).sum())
    print('[self2] 记录矩形 (别人的采样窗) 被动过的像素: %d (期望 0)' % bad_px)
    assert bad_px == 0, '记录码/图标码的采样窗被改了!'

    # ---------- 自检 3: 每个字的字形原样落到**它最终该在**的格 ----------
    move_by_char = dict((m['char'], m) for m in moves)
    miss_src, extra, lost, no_dest, clipped = [], [], [], [], []
    for slot, ch in sorted(by_slot.items()):
        row, col = slot // NCOL, slot % NCOL
        if row not in ROWS or yrow(row) + CH > H:
            continue
        m = move_by_char.get(ch)
        drow, dcol = (m['new_row'], m['new_col']) if m else (row, col)
        if blocked(drow, dcol):
            no_dest.append((drow, dcol, ch))
            continue
        g = glyphs.get((row, col))
        cell = En[yrow(drow):yrow(drow) + CH, dcol * CW:(dcol + 1) * CW]
        if g is None or not g.any():
            miss_src.append((row, col, ch))
            if cell.any():
                extra.append((drow, dcol, ch))
            continue
        if not (cell == g).all():
            if m is None and blocked(drow, dcol):
                clipped.append((drow, dcol, ch, int((cell != g).sum())))
            else:
                lost.append((drow, dcol, ch, int((cell != g).sum())))
    print('[self3] 没有可用目标格的已用槽 (期望 0): %d %s' % (len(no_dest), no_dest[:4]))
    print('[self3] 源盘上就没字形的已用槽 (既有缺字, 与本轮无关): %d 个 %s'
          % (len(miss_src), ''.join(c for _, _, c in miss_src)))
    print('[self3] 这些槽在新图里意外有墨的 (期望 0): %d' % len(extra))
    print('[self3] 有字形但没原样落到新格的 (期望 0): %d %s' % (len(lost), lost[:4]))
    print('[self3] 因格被记录矩形压着而缺像素的槽 (期望 0): %d %s' % (len(clipped), clipped[:4]))
    assert not lost and not extra and not no_dest and not clipped, '字形搬运不正确'

    # ---------- 回写容器 (逐像素, 只写数据区, 不碰包头) ----------
    changed = np.where(diff)
    nb = np.frombuffer(bytes(A.nib), dtype=np.uint8)
    tot = np.bincount(nb & 0x0F, minlength=16) + np.bincount(nb >> 4, minlength=16)
    tot[0] = 0
    empty_val = int(np.argmax(tot))
    assert 1 <= empty_val <= 15, empty_val
    print()
    print('[pack] 「空」用调色板索引 %d (全体 nibble 直方图 %s)'
          % (empty_val, ' '.join('%X:%d' % (i, tot[i]) for i in range(16))))
    for y, x in zip(changed[0].tolist(), changed[1].tolist()):
        A.set_px(int(x), int(y), bool(En[y, x]), empty_val)
    back, _cov = A.decode_engine()
    if not (back == En).all():
        bd = np.where(back != En)
        print('[pack] !! 回写后引擎图不一致 %d 处, 前 6 个: %s'
              % (len(bd[0]), [(int(y), int(x)) for y, x in list(zip(*bd))[:6]]))
    assert (back == En).all(), '回写后引擎图与目标图不一致'
    print('[pack] 回写 %d 像素完成, 重新解出引擎图核对一致 ✓' % len(changed[0]))

    if dry:
        print('[dry ] 不写盘。')
        return 0

    shutil.copyfile(src, dst)
    with open(dst, 'r+b') as f:
        f.seek(pak_e['iso_off'] + PX)          # ★ 像素容器在 PAK 内的偏移 = PX (别写到 PAK 头!)
        f.write(bytes(A.nib))
    assert os.path.getsize(src) == os.path.getsize(dst), 'ISO 尺寸变了!'
    print('[iso ] → %s (尺寸不变 %d B)' % (dst, os.path.getsize(dst)))

    # ---------- charset ----------
    if do_charset:
        cs_path = tcslib.CHARSET
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        if not os.path.exists(BACKUP):
            shutil.copyfile(cs_path, BACKUP)
            print('[json] 备份原 charset → %s' % BACKUP)
        js = json.load(io.open(cs_path, encoding='utf-8'))
        for m in moves:
            ch = m['char']
            old = js['pair_of'].get(ch)
            assert old and tcslib.pair_slot(*old) == m['old_slot'], (ch, old, m)
            lead = tcslib.PAIR_LEAD_LO + m['new_slot'] // tcslib.PAIR_STRIDE
            trail = tcslib.PAIR_TRAIL_LO + m['new_slot'] % tcslib.PAIR_STRIDE
            assert tcslib.PAIR_LEAD_LO <= lead < tcslib.PAIR_LEAD_HI, lead
            assert tcslib.PAIR_TRAIL_LO <= trail <= tcslib.PAIR_TRAIL_HI, trail
            js['pair_of'][ch] = [lead, trail]
            m['new_code'] = '%02X%02X' % (lead, trail)
        bad = [(s, ch) for ch, v in js['pair_of'].items()
               for s in [tcslib.pair_slot(*v)]
               if tcslib.ATLAS_ENGINE_SINGLE_CELLS.get((s // NCOL, s % NCOL))]
        assert not bad, '还有字落在记录码压着的格上: %s' % bad[:5]
        js['_glyph_align_zh94'] = dict(
            note='round45: grid 行 19..24 的字形搬到引擎采样格 (16*col, yrow); '
                 '与 FT 记录矩形 (单字节码/手柄图标码的采样窗) 冲突的格不能给对偶码用 '
                 '(见 docs/REPORT_glyph_align.md)',
            phi_new=dict((str(r), new_phi(r)) for r in ROWS),
            moved=dict((m['char'], '%s slot=%d (row%d col%d)' %
                        (m['new_code'], m['new_slot'], m['new_row'], m['new_col']))
                       for m in moves),
            forbidden_cells=dict(('%d,%d' % rc, v)
                                 for rc, v in sorted(tcslib.ATLAS_ENGINE_SINGLE_CELLS.items())))
        io.open(cs_path, 'w', encoding='utf-8', newline='\n').write(
            json.dumps(js, ensure_ascii=False, indent=1) + '\n')
        print('[json] charset 已更新: %d 个字改派新对偶码' % len(moves))
        cs2 = tcslib.Charset()
        for m in moves:
            assert m['char'] in cs2.enc_pair and m['char'] not in cs2.enc_single, m
            assert tcslib.pair_slot(*cs2.enc_pair[m['char']]) == m['new_slot'], m
            assert cs2.encode_strict(m['char']) == bytes(
                [tcslib.PAIR_LEAD_LO + m['new_slot'] // tcslib.PAIR_STRIDE,
                 tcslib.PAIR_TRAIL_LO + m['new_slot'] % tcslib.PAIR_STRIDE]), m
        print('[json] 新 charset 自检 ✓ (改派后的码位/编码/槽位三者一致)')

    # ---------- 回读核验 ----------
    with open(dst, 'rb') as f:
        f.seek(pak_e['iso_off'])
        pak2 = f.read(pak_e['stored'])
    recs2 = [r for r in tcslib.parse_pak_records(pak2) if r[0] == 'new_font_revised']
    assert len(recs2) == 1, '回读: COMMON.PAK 记录链读不出来 (PAK 被写坏?)'
    assert (bytes(pak2[:PX]) == bytes(pak[:PX])
            and bytes(pak2[PX + W * H // 2:]) == bytes(pak[PX + W * H // 2:])), \
        '回读: 像素容器以外的 PAK 字节被改动了!'
    print('[ver ] 回读: PAK 里除像素容器外**逐字节不变** ✓')
    A2 = Atlas(bytearray(pak2), recs2[0][6], px_size)
    assert recs2[0][6] == PX, (recs2[0][6], PX)
    assert (A2.decode_engine()[0] == En).all(), '回读引擎图与目标图不一致'
    print('[ver ] 回读: 盘上解出的引擎图 == 目标图 ✓')

    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    io.open(REPORT, 'w', encoding='utf-8', newline='\n').write(json.dumps(dict(
        src=os.path.relpath(src, REPO), dst=os.path.relpath(dst, REPO),
        phi_old=dict((str(r), tcslib.atlas_row_phase(r)) for r in ROWS),
        phi_new=dict((str(r), new_phi(r)) for r in ROWS),
        rec_cells=[dict(cell='%d,%d' % rc, note=v)
                   for rc, v in sorted(tcslib.ATLAS_ENGINE_SINGLE_CELLS.items())],
        moved=moves, placed=len(placed), skipped=len(skipped),
        missing_before=[list(x) for x in miss_src],
        pixels_changed=int(diff.sum())), ensure_ascii=False, indent=1) + '\n')
    print('[rep ] → %s' % REPORT)
    return 0


if __name__ == '__main__':
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    sys.exit(main(a[0], a[1], dry='--dry-run' in sys.argv,
                  do_charset='--no-charset' not in sys.argv))
