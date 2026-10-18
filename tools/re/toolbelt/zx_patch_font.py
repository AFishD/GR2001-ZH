# -*- coding: utf-8 -*-
r"""zx_patch_font.py — 「零缺字成品盘」核心补丁 (round82)

    python zx_patch_font.py <src.iso> <dst.iso> [--p1] [--dry-run] [--prep-text] [--report F]

做四件事（`--p1` 只做第 1+2 件，用于实机单变量探针）:

  ① COMMON.PAK 记录 `new_font_revised`: h 512→640, px_size 0x40010→0x501F0,
     像素容器重切成 **10 段自闭合 GIF 包**（每段 64 行 0x8000 B + 48 B 包头）+ 尾部 16 B no-op tag。
     行 0..510 逐字节复制（段 0..6 整段照搬; 段 7 的 32,384 B 照搬 + 384 B 填 0x11）,
     行 512..639 填 0x11（调色板索引 1 = 透明）。
  ② COMMON.PAK 原地长大 +66,016 B ⇒ MENU.IMG 里 FONT.RES 起的 682 个条目 off 全体 +66,016,
     MENU.IMG 声明长度 +4,780（= 66,016 − 容器内尾料 61,236）,**ISO 文件尺寸不变**。
  ③ [full] **搬两条活带**: FONT.RES 里 (452,468)×332 条与 (482,498)×56 条记录的 v0/v1
     改到 (594,610)/(610,626)（Δv = +142 / +128）, 像素同步搬到新 y;
     FONT.RES 槽内 LZO 子流**重压写回**(stored 保持 4421, 展开长度保持 5942)。
  ④ [full] 把 368 个字形画进新格 slot 1504..1871（行 24 尾 16..61 / 行 25..29 全行 / 行 30 col 0..11）:
     364 个缺字（方正像素16, 「嘚」用系统 simhei 兜底）+ 迁移字 △/键/练/用。
  ⑤ [full] ELF 4 处 gate `sltiu …,0xB1` → `…,0xB5`（0x416EE8 / 0x417160 / 0x41751C / 0x5656A4）。

写盘后跑六条硬断言（见 docs/REPORT_zero_missing_glyph_build2.md）。
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
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                   # noqa: E402
import zx_lib                                                        # noqa: E402  (会先插好 sys.path)
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
W, H_OLD, H_NEW = 1024, 512, 640
R81 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
R82 = zx_lib.OUT
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
SIMHEI = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simhei.ttf')
N_NEW = 368                                  # 364 缺字 + 4 迁移字
SLOT_LO = 1504
GATE_SITES_VA = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
ELF_ISO_BASE = 0x93880
ELF_VA_BASE = 0x100000
BAND_OLD = (zx_lib.BAND_EN_OLD, zx_lib.BAND_KB_OLD)
BAND_NEW = (zx_lib.BAND_EN_NEW, zx_lib.BAND_KB_NEW)
MIGRATE = [('△', 0xB1, 0xA1), ('键', 0xB1, 0xA2), ('练', 0xB1, 0xA3), ('用', 0xB1, 0xA4)]

LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ═══════════════════════ 字形来源 ═══════════════════════

def render16_simhei(ch):
    """与 gen_font16.render16 同款配方, 只是换字体 (「嘚」的系统兜底)。"""
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(SIMHEI, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=f, fill=0)
    a = np.asarray(img)
    return a[8:24, 8:24] < 128


def hex_to_bitmap(hx):
    g = np.zeros((16, 16), dtype=bool)
    for y in range(16):
        v = int(hx[y], 16)
        for x in range(16):
            g[y, x] = bool((v >> (15 - x)) & 1)
    return g


def triangle16():
    """△ 字形 (16x16, 空心三角 + 底横): 与 P2 判据"必须是三角图标"对齐。"""
    g = np.zeros((16, 16), dtype=bool)
    # 边: 顶点 (7,2) → 左下 (2,13) / 右下 (13,13), 线宽 2
    def line(x0, y0, x1, y1, w=1):
        n = max(abs(x1 - x0), abs(y1 - y0)) * 2
        for i in range(n + 1):
            t = i / float(n)
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            for dx in range(w):
                for dy in range(w):
                    if 0 <= x + dx < 16 and 0 <= y + dy < 16:
                        g[y + dy, x + dx] = True
    line(7, 2, 2, 13)
    line(8, 2, 13, 13)
    line(2, 13, 13, 13)
    line(3, 13, 12, 13)
    return g


def load_glyphs():
    """→ [(char, bitmap|None, 来源说明)] ; None = 需要从旧图集/图标源抠 (main 里填)"""
    items = {}
    gj = json.load(io.open(os.path.join(R81, 'glyphs_zh120.json'), encoding='utf-8'))
    for it in gj['items']:
        items[it['char']] = it
    miss = []
    with io.open(os.path.join(R82, 'rich_missing_chars.csv'), encoding='utf-8-sig',
                 newline='') as f:
        for r in csv.DictReader(f):
            miss.append(r['char'])
    P('[glyph] r81 glyphs %d 条 ; r82 缺字清单 %d 条 ; 集合一致: %s'
      % (len(items), len(miss), set(items) == set(miss)))
    assert set(items) == set(miss), (sorted(set(items) ^ set(miss))[:10])
    out = []
    n_fb = 0
    for ch in miss:
        it = items[ch]
        if it.get('hex'):
            g = hex_to_bitmap(it['hex'])
            src = 'fz16 (r81 render16 同款配方)'
        else:
            g = render16_simhei(ch)
            src = 'simhei.ttf 兜底 (现役同配方)'
            n_fb += 1
        assert g.any(), '空字形 %r' % ch
        out.append((ch, g, src))
    P('[glyph] 364 个缺字字形就绪 (方正 %d + simhei 兜底 %d %s)'
      % (364 - n_fb, n_fb, [c for c, g, s in out if 'simhei' in s]))
    for ch, b1, b2 in MIGRATE:
        if ch == '△':
            out.append((ch, triangle16(), '手绘三角 (引擎图标在 pda_counterparts, 20x20 彩色, '
                                          '不能直接当 1-bit 字形)'))
        else:
            out.append((ch, None, 'copy rec'))
    return out, n_fb


# ═══════════════════════ 主流程 ═══════════════════════

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--p1', action='store_true', help='只做数据侧 (h/px_size/容器/MENU 平移)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--prep-text', action='store_true',
                    help='顺带把注入用文本表写到 <dst 目录>/text_in/')
    ap.add_argument('--apply-charset', action='store_true',
                    help='顺带更新 tools/font_pipeline/data/charset_compiled_zh16.json '
                         '(368 条新码位 + 4 条迁移; 原文件备份到 r82/charset_before_r82.json)')
    ap.add_argument('--report', default=os.path.join(R82, 'patch_font_report.json'))
    ap.add_argument('--h-declared', type=lambda s: int(s, 0), default=None,
                    help='★ 实验用: 记录里 h 字段改成的值 (默认 = 容器实际行数 640)。'
                         '用于验证"引擎按 h 分配纹理行数"这一假设 (h=1024 ⇒ 分配 1024 行)')
    ap.add_argument('--grow-only', action='store_true',
                    help='★ 实验用: 只做 COMMON.PAK 长大 + MENU 平移 (图集/px_size/h 一律不动)')
    a = ap.parse_args(argv)
    src, dst = a.src, a.dst
    full = not a.p1
    if not a.dry_run:
        assert dst, '需要 <dst.iso>'
    P('=' * 78)
    P('zx_patch_font.py  mode=%s' % ('FULL' if full else 'P1(数据侧单变量)'))
    P('  src = %s' % src)
    P('  dst = %s' % (dst or '(dry-run)'))
    P('=' * 78)

    iso = tcslib.Iso(src)
    ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
    hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    P('[img] MENU.IMG 条目 %d ; #%d COMMON.PAK off=0x%X stored=%d ; #%d FONT.RES off=0x%X stored=%d'
      % (len(ents), e_pak['idx'], e_pak['off'], e_pak['stored'], e_ft['idx'], e_ft['off'],
         e_ft['stored']))
    assert (e_pak['idx'], e_pak['off'], e_pak['stored']) == (3, 0x57400, 400659)
    assert (e_ft['idx'], e_ft['off'], e_ft['stored'], e_ft['real']) == (4, 0xB9120, 4421, 7222)
    names0 = zx_lib.names_region(iso, zx_lib.MENU_LBA)
    hash0 = zx_lib.hash_region(iso, zx_lib.MENU_LBA)
    base_menu = bytes(iso.mm[zx_lib.MENU_LBA * zx_lib.SEC:
                             zx_lib.MENU_LBA * zx_lib.SEC + hdr['size']])
    pak = bytearray(iso.read(e_pak['iso_off'], e_pak['stored']))
    ft_slot = iso.read(e_ft['iso_off'], e_ft['stored'])

    # ---- 记录定位 ----
    recs = tcslib.parse_pak_records(bytes(pak))
    assert len(recs) == 4, [r[0] for r in recs]
    nm, psm, aw, ah, clut, px_size, PX = recs[1]
    assert (nm, psm, aw, ah, clut, px_size) == ('new_font_revised', 0x14, W, H_OLD, 0x410,
                                                0x40010)
    # 字段偏移: psm@q, w@q+4, h@q+8, clut@q+12, px@q+16+clut
    # 由 parse_pak_records 的解析反推 q: px_off = q+20+clut ⇒ q = PX-20-clut
    q = PX - 20 - clut
    assert struct.unpack_from('<4I', pak, q) == (psm, aw, ah, clut)
    assert struct.unpack_from('<I', pak, q + 16 + clut)[0] == px_size
    P('[pak] new_font_revised psm=0x%02X %dx%d clut=0x%X px_size=0x%X @PAK+0x%X ; 字段 @PAK+0x%X'
      % (psm, aw, ah, clut, px_size, PX, q))

    old_ct = bytes(pak[PX:PX + px_size])
    segs_old = zx_lib.seg_table(old_ct, W)
    prefs, ssa_off = zx_lib.seg_prefixes(old_ct, W)
    trailer = old_ct[-16:]
    P('[ct ] 旧容器 %d 段 %s ; SSAY 字段偏移 %d ; 尾部 tag %s'
      % (len(segs_old), [(s[0], s[2]) for s in segs_old], ssa_off,
         ' '.join('%02X' % b for b in trailer)))
    img_old, cov_old = zx_lib.decode_engine(old_ct, W, H_OLD)
    P('[ct ] 旧引擎图: 覆盖 %d texel, 墨 %d texel (1024x512)'
      % (int(cov_old.sum()), int(img_old.sum())))

    # ---- 新容器 ----
    wr = zx_lib.AtlasWriter(W, H_NEW, prefix_tpl=prefs[0][2], ssa_off=ssa_off, trailer=trailer)
    assert wr.nseg == 10, wr.nseg
    for k, (row, doff, nb) in enumerate(segs_old):
        wr.set_segment(k, old_ct[doff:doff + nb])
    P('[ct ] 新容器 %d 段 = 10*48 + 10*0x8000 + 16 = 0x%X (= %d)'
      % (wr.nseg, len(wr.bytes()), len(wr.bytes())))
    assert len(wr.bytes()) == 0x501F0

    info = dict(mode='full' if full else 'p1', cells=[])
    # ---- FONT.RES 展开态 + 记录 (P1 只读不改, full 要改 v0/v1) ----
    exp = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
    assert len(exp) == 5942, len(exp)
    faces, endp = zx_lib.ft_records(exp, 28)
    nrecs = [(f[0], f[1][4] * f[1][5]) for f in faces]
    P('[ft  ] 展开 %d B, faces %s, styles 起点 0x%X' % (len(exp), nrecs, endp))
    assert nrecs == [('large', 224), ('default', 224), ('huge', 96)]
    recs_all = [r for (_f, _fl, rows) in faces for (_ro, r) in rows]
    glyphs = []
    if full:
        # 目标展开态: 只改两条活带的 v0/v1
        tgt = bytearray(exp)
        tgt_changes = {}
        nband = {BAND_OLD[0]: 0, BAND_OLD[1]: 0}
        for (fname, fld, rows) in faces:
            for (roff, r) in rows:
                b0, b1, u0, v0, u1, v1 = r
                if (v0, v1) in BAND_NEW:
                    continue
                if (v0, v1) == BAND_OLD[0]:
                    nv0, nv1 = BAND_NEW[0]
                elif (v0, v1) == BAND_OLD[1]:
                    nv0, nv1 = BAND_NEW[1]
                else:
                    continue
                assert u1 > u0, (fname, r)
                nband[(v0, v1)] += 1
                for fo, old, new in ((roff + 4, v0, nv0), (roff + 8, v1, nv1)):
                    ob, nb = struct.pack('<H', old), struct.pack('<H', new)
                    for kk in range(2):
                        if ob[kk] != nb[kk]:
                            tgt[fo + kk] = nb[kk]
                            tgt_changes[fo + kk] = nb[kk]
        P('[ft  ] 目标: 改 %d 个展开态字节 (%d 条 EN 带 + %d 条键盘带 x 3/2 个 face)'
          % (len(tgt_changes), nband[BAND_OLD[0]], nband[BAND_OLD[1]]))
        assert nband[BAND_OLD[0]] == 276 and nband[BAND_OLD[1]] == 56, nband

        # 字形装配
        gl, n_fb = load_glyphs()
        # 迁移字: 从旧引擎图按记录窗口抠 (键/练/用)
        keyrec = {'键': 146, '练': 147, '用': 148}
        fixed = []
        for (ch, g, srcid) in gl:
            if g is None:
                idx = keyrec[ch]
                roff, r = faces[1][2][idx]          # default face
                b0, b1, u0, v0, u1, v1 = r
                g = img_old[v0 + zx_lib.GLYPH_DV:v0 + zx_lib.GLYPH_DV + 16,
                            u0 + zx_lib.GLYPH_DU:u0 + zx_lib.GLYPH_DU + 16].copy()
                assert g.shape == (16, 16), (ch, g.shape, r)
                assert g.any(), '%r 在旧图集上零墨' % ch
                srcid = '旧图集 rec[%d] 采样窗 (%d,%d) 原样抠 (墨 %d)' \
                        % (idx, u0 + 4, v0 + 2, int(g.sum()))
            fixed.append((ch, g, srcid))
        glyphs = fixed
        assert len(glyphs) == N_NEW, len(glyphs)
        P('[glyph] %d 个字形:' % len(glyphs))
        for i in (0, 1, 2, 363, 364, 365, 366, 367):
            ch, g, srcid = glyphs[i]
            P('        slot %d %r 墨 %d  来源 %s' % (SLOT_LO + i, ch, int(g.sum()), srcid))

        info['cells'] = []
        # ---- 搬带: 先把旧窗口像素搬到新位置 ----
        for (bo, bn) in zip(BAND_OLD, BAND_NEW):
            bw = zx_lib.band_windows(faces[1][2] + faces[0][2] + faces[2][2], bo)
            assert bw, bo
            x0, x1, y0, y1 = bw
            dy = bn[0] - bo[0]
            assert (bn[1] - bo[1]) == dy
            blk = img_old[y0:y1, x0:x1].copy()
            P('[band] %s 采样窗 x[%d,%d) y[%d,%d) Δy=%+d ⇒ 墨 %d texel 搬到 y[%d,%d)'
              % (bo, x0, x1, y0, y1, dy, int(blk.sum()), y0 + dy, y1 + dy))
            for yy in range(blk.shape[0]):
                for xx in range(blk.shape[1]):
                    wr.set_px(x0 + xx, y0 + dy + yy, bool(blk[yy, xx]))
            assert y1 + dy <= H_NEW

        # ---- 画字形 ----
        cells = []
        for i, (ch, g, srcid) in enumerate(glyphs):
            slot = SLOT_LO + i
            x, y = zx_lib.slot_cell(slot)
            assert y + 16 <= H_NEW and x + 16 <= W
            for yy in range(16):
                for xx in range(16):
                    wr.set_px(x + xx, y + yy, bool(g[yy, xx]))
            cells.append((ch, slot, x, y, g))
        info['cells'] = [(c, s, x, y) for (c, s, x, y, _g) in cells]
        P('[draw] %d 格已画: slot %d..%d ; 行 %d..%d ; y %d..%d'
          % (len(cells), cells[0][1], cells[-1][1], cells[0][3] // 16, cells[-1][3] // 16,
             min(c[3] for c in cells), max(c[3] for c in cells) + 16))

    if a.grow_only:
        new_ct = old_ct
        img_new, cov_new = zx_lib.decode_engine(new_ct, W, H_OLD)
        H_CT = H_OLD
    else:
        new_ct = wr.bytes()
        img_new, cov_new = zx_lib.decode_engine(new_ct, W, H_NEW)
        H_CT = H_NEW
    P('[ct ] 新引擎图: 覆盖 %d texel ; 墨 %d texel' % (int(cov_new.sum()), int(img_new.sum())))
    if not a.grow_only:
        assert cov_new[0:H_OLD].all(), '行 0..511 覆盖不全'

    # ---- 组装新 PAK ----
    pak2 = bytearray(pak)
    if a.grow_only:
        new_ct = old_ct
        # ★ 长大必须发生在**记录链结束哨兵 (0x63) 之后**: 直接追加零, 不能插在容器与 pda 记录之间
        #   (插中间会把记录链读成垃圾 —— 这就是 round31 探针 B 的做法)
        new_pak = bytes(pak2) + b'\x00' * 66016
        P('[pak] --grow-only: 图集/px_size/h 全不动, 在记录链哨兵之后追加 66,016 B 零')
    else:
        struct.pack_into('<I', pak2, q + 8, a.h_declared or H_NEW)
        struct.pack_into('<I', pak2, q + 16 + clut, 0x501F0)
        new_pak = bytes(pak2[:PX]) + new_ct + bytes(pak2[PX + px_size:])
        if a.h_declared:
            P('[pak] ★ --h-declared 0x%X: 记录 h=%d (容器仍是 %d 行 / px_size 0x501F0)'
              % (a.h_declared, a.h_declared, H_NEW))
    delta = len(new_pak) - len(pak)
    P('[pak] COMMON.PAK %d → %d B (Δ = %+d, 期望 +66,016)' % (len(pak), len(new_pak), delta))
    assert delta == 66016, delta
    recs2 = tcslib.parse_pak_records(new_pak)
    assert len(recs2) == 4, [r[0] for r in recs2]
    if not a.grow_only:
        assert recs2[1][5] == 0x501F0, recs2[1][5]
        assert recs2[2][6] == recs[2][6] + delta and recs2[3][6] == recs[3][6] + delta
    else:
        assert [r[6] for r in recs2] == [r[6] for r in recs], 'grow-only 模式下记录链不该动'
    P('[pak] 回读: %s' % [(r[0], r[2], r[3], hex(r[5]), hex(r[6])) for r in recs2])

    # ---- 新 FONT.RES 槽 (full) ----
    new_ft = ft_slot
    if full:
        cc = tcslib.lzo_compress(bytes(tgt), level=7, use_m1=True, use_m4=True)
        back, err, _ = tcslib.lzo1x_decompress(cc, out_size=len(tgt))
        assert err is None and back == bytes(tgt), 'FONT.RES 重压回环失败'
        new_ft = (struct.pack('<II', len(cc), len(tgt)) + cc).ljust(len(ft_slot), b'\x00')
        assert len(new_ft) == len(ft_slot), (len(new_ft), len(ft_slot))
        exp2 = b''.join(s[0] for s in tcslib.lzo_subs(new_ft))
        assert len(exp2) == 5942, len(exp2)
        diffs = [i for i in range(5942) if exp2[i] != exp[i]]
        assert set(diffs) == set(tgt_changes), (len(diffs), len(tgt_changes))
        P('[ft  ] 新槽 %d B (帧 %d + 零填充 %d) ; 展开 %d B ; 差异 %d 字节 == 目标集合 ✓'
          % (len(new_ft), 8 + len(cc), len(new_ft) - 8 - len(cc), len(exp2), len(diffs)))

    # ---- 组装新 MENU.IMG ----
    #   ★★ 关键: 新声明长度必须 **扇区对齐**。IMG 是被引擎按扇区整块读进来的
    #      (round31 探针 A/B 实机验证过的值是 58,331,136 = 28,482 扇区 = 正好到 ISO 卷尾)。
    #      若只声明到"最后一个条目的字节末尾"(58,305,662, 非扇区对齐), 引擎读到的
    #      扇区圆整长度会短 1,150 B ⇒ 最后一个条目 (EN_STRINGS.TXT) 尾部读不到。
    #      实测: 非对齐版本实机黑屏卡死 (GIF upload 0 次 / 0 张截图)。
    MAX_MENU = 804768 * 2048 - zx_lib.MENU_LBA * 2048          # = 58,331,136 (ISO 卷尾)
    last_end = max(e['off'] + e['stored'] for e in ents)
    need = last_end + delta
    new_size = MAX_MENU if need <= MAX_MENU else ((need + 2047) // 2048) * 2048
    assert new_size % 2048 == 0 and new_size >= need, (new_size, need)
    P('[menu] 容器: 旧声明 %d, 条目最大 end %d, 新 end %d ⇒ 新声明 %d (Δ = %+d, ISO 尾用掉 %d, '
      '%d 扇区)'
      % (hdr['size'], last_end, need, new_size, new_size - hdr['size'],
         new_size - hdr['size'], new_size // 2048))
    max_grow = MAX_MENU - hdr['size']
    assert new_size - hdr['size'] <= max_grow, (new_size, max_grow)
    new_menu = bytearray(new_size)
    new_menu[0:e_pak['off']] = base_menu[0:e_pak['off']]
    new_menu[e_pak['off']:e_pak['off'] + len(new_pak)] = new_pak
    ft_new_off = e_ft['off'] + delta
    new_menu[ft_new_off:ft_new_off + len(new_ft)] = new_ft
    tail_src = base_menu[e_ft['off'] + len(ft_slot):last_end]
    new_menu[ft_new_off + len(new_ft):need] = tail_src
    assert len(tail_src) == need - (ft_new_off + len(new_ft)), \
        (len(tail_src), need - (ft_new_off + len(new_ft)))
    struct.pack_into('<I', new_menu, 0, new_size)
    # 条目表
    chg = []
    for e in ents:
        if e['off'] >= e_ft['off']:
            newoff = e['off'] + delta
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             newoff)
            chg.append((e['idx'], 'off', e['off'], newoff))
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
            chg.append((e['idx'], 'stored', e['stored'], e['stored'] + delta))
    P('[menu] 条目表改动 %d 处 (off %d 条 + stored 1 条)'
      % (len(chg), sum(1 for c in chg if c[1] == 'off')))
    assert len(chg) == 682 + 1, len(chg)
    # 名字区 / 哈希表必须一字不动
    assert bytes(new_menu[hdr['names_start']:hdr['names_end']]) == names0
    assert bytes(new_menu[hdr['hash_off']:hdr['hash_off'] + 16384]) == hash0
    P('[menu] 名字区 %d B / 4096 槽表 16,384 B **逐字节不变** ✓' % len(names0))

    if a.dry_run:
        P('\n[dry ] --dry-run: 不写盘。')
        # 六条断言仍然全跑 (对内存态)
    else:
        shutil.copyfile(src, dst)
        with open(dst, 'r+b') as f:
            f.seek(zx_lib.MENU_LBA * zx_lib.SEC)
            f.write(bytes(new_menu))
            # ISO9660 目录记录 data length
            f.seek(0x828D8)
            f.write(struct.pack('<I', new_size) + struct.pack('>I', new_size))
            if full:
                for va in GATE_SITES_VA:
                    off = ELF_ISO_BASE + va - ELF_VA_BASE
                    f.seek(off)
                    b = bytearray(f.read(4))
                    assert b[0] == 0xB1, (hex(va), b.hex(' '))
                    b[0] = 0xB5
                    f.seek(off)
                    f.write(bytes(b))
        assert os.path.getsize(dst) == os.path.getsize(src), 'ISO 尺寸变了'
        P('[iso ] → %s (尺寸不变 %d B)' % (dst, os.path.getsize(dst)))

    # ═══════════════ 六条硬断言 (从盘/内存态回读) ═══════════════
    if not a.dry_run:
        iso2 = tcslib.Iso(dst)
        ents2 = zx_lib.entries(iso2, zx_lib.MENU_LBA)
        hdr2 = zx_lib.header(iso2, zx_lib.MENU_LBA)
        e_pak2 = ents2[e_pak['idx']]
        pak_r = iso2.read(e_pak2['iso_off'], e_pak2['stored'])
        recs_r = tcslib.parse_pak_records(pak_r)
        ct_r = pak_r[recs_r[1][6]:recs_r[1][6] + recs_r[1][5]]
        img_r, cov_r = zx_lib.decode_engine(ct_r, W, H_CT)
        ft_r = iso2.read(ents2[e_ft['idx']]['iso_off'], ents2[e_ft['idx']]['stored'])
        menu_r = bytes(iso2.mm[zx_lib.MENU_LBA * zx_lib.SEC:
                               zx_lib.MENU_LBA * zx_lib.SEC + hdr2['size']])
        iso2.close()
        P('\n' + '─' * 78)
        P('写盘后硬断言')
        P('─' * 78)
        assert img_r.shape == (H_CT, W)
        assert (img_r == img_new).all(), '盘上解出的引擎图 != 目标引擎图'
        P('④ 段表回读 == 目标 (逐 texel, %d x %d) ✓' % (W, H_CT))
        info['assert4'] = True

        # ① 行 0..511 被引用矩形逐字节不变
        bad = []
        for slot in range(1504):
            x, y = tcslib.atlas_cell_xy_engine_view(slot)
            if not (img_r[y:y + 16, x:x + 16] == img_old[y:y + 16, x:x + 16]).all():
                bad.append(slot)
        assert not bad, '现役 pair 格被改动: %s' % bad[:5]
        # 所有 FT 记录窗 (3 face) 里, 除"被搬走的旧带"外必须逐像素不变
        n_rec_chk = 0
        n_band_skipped = 0
        for r in recs_all:
            b0, b1, u0, v0, u1, v1 = r
            if u1 <= u0:
                continue
            x0, y0 = u0 + zx_lib.GLYPH_DU, v0 + zx_lib.GLYPH_DV
            if full and (v0, v1) in BAND_OLD:
                n_band_skipped += 1
                continue
            if y0 + (v1 - v0) > H_OLD:
                continue
            if not (img_r[y0:y0 + (v1 - v0), x0:x0 + (u1 - u0)]
                    == img_old[y0:y0 + (v1 - v0), x0:x0 + (u1 - u0)]).all():
                raise AssertionError('FT 记录矩形被改动: %s' % (r,))
            n_rec_chk += 1
        P('① 行 0..511: 现役 1504 个 pair 格 **逐字节不变** ✓ ; '
          'FT 记录矩形 %d 条逐字节不变 ✓ %s'
          % (n_rec_chk, ('(两条活带 %d 条按设计搬走)' % n_band_skipped) if full
             else '(两条活带原地未动)'))
        # 行 0..511 除目标格外**逐像素不变** (P1 是全域; full 是"除 368 格 + 旧带"外)
        cells_mask = np.zeros((H_CT, W), dtype=bool)
        for (_c, _s, x, y) in info['cells']:
            cells_mask[y:y + 16, x:x + 16] = True
        band_mask = np.zeros((H_CT, W), dtype=bool)
        if full:
            for (bo, bn) in zip(BAND_OLD, BAND_NEW):
                x0, x1, y0, y1 = zx_lib.band_windows(recs_all, bo)
                dy = bn[0] - bo[0]
                band_mask[y0 + dy:y1 + dy, x0:x1] = True
        oldrows_diff = (img_r[:H_OLD, :] != img_old[:H_OLD, :])
        stray_old = oldrows_diff & ~cells_mask[:H_OLD, :] & ~band_mask[:H_OLD, :]
        assert not stray_old.any(), '行 0..511 出现计划外像素改动 %d 个' % int(stray_old.sum())
        P('①c 行 0..511 的计划外像素改动 = 0 (改动像素 %d 个, 全部落在 %s)'
          % (int(oldrows_diff.sum()),
             '368 个目标格内' if full else '无 (P1 全等)'))
        if full:
            # 搬带的内容等价性
            for (bo, bn) in zip(BAND_OLD, BAND_NEW):
                bw = zx_lib.band_windows(recs_all, bo)
                x0, x1, y0, y1 = bw
                dy = bn[0] - bo[0]
                assert (img_r[y0 + dy:y1 + dy, x0:x1] == img_old[y0:y1, x0:x1]).all(), bo
            P('①b 两条活带的像素**原样搬到新 y** (窗口内容逐像素相等) ✓')

        # ② 新墨点全部落在目标格 / 搬带窗内
        allowed = cells_mask | band_mask
        newrows = np.zeros((H_CT, W), dtype=bool)
        newrows[H_OLD:, :] = True
        outside = (img_r != np.vstack([img_old, np.zeros((H_CT - H_OLD, W), dtype=bool)])) \
            & ~allowed & ~newrows
        assert not outside.any(), '格外墨点改动 %d 个' % int(outside.sum())
        # 新行里除 band/格 之外的墨必须是 0 (背景)
        stray = img_r[H_OLD:, :] & ~allowed[H_OLD:, :]
        assert not stray.any(), '新行区出现计划外墨点 %d 个' % int(stray.sum())
        P('② 新墨点全部落在目标格/搬带窗内 (格外改动 = 0, 新行区杂散墨 = 0) ✓ '
          '[新行区墨 %d texel]' % int(img_r[H_OLD:, :].sum()))
        # 每个格的墨量与字形逐点一致
        if full:
            for (c, s, x, y) in info['cells']:
                g = [gg for (cc, gg, _sd) in glyphs if cc == c][0]
                assert (img_r[y:y + 16, x:x + 16] == g).all(), c
            P('②b 368 个格回读 == 16px 字形模板 (逐像素) ✓')

        # ③ 字节级: 允许区
        P('③ 字节级: 新容器长度 %d (旧 %d, Δ = %+d) ; 改动只发生在 (新行区 ∪ 目标格 ∪ 搬带窗)'
          % (len(ct_r), len(old_ct), len(ct_r) - len(old_ct)))

        # ⑤ FONT.RES
        exp_r = b''.join(s[0] for s in tcslib.lzo_subs(ft_r))
        faces_r, endp_r = zx_lib.ft_records(exp_r, 28)
        nrecs_r = [(f[0], f[1][4] * f[1][5]) for f in faces_r]
        assert nrecs_r == nrecs, (nrecs_r, nrecs)
        assert len(exp_r) == 5942 and endp_r == 0x1620
        assert ents2[e_ft['idx']]['stored'] == 4421, ents2[e_ft['idx']]['stored']
        diffs_r = []
        if full:
            diffs_r = [i for i in range(5942) if exp_r[i] != exp[i]]
            assert set(diffs_r) == set(tgt_changes), len(diffs_r)
        else:
            assert exp_r == exp, 'P1 模式 FONT.RES 展开态被动过'
        P('⑤ FONT.RES: stored %d 不变, 展开 %d B 不变, 记录数 %s 不变, 差异 %s ✓'
          % (ents2[e_ft['idx']]['stored'], len(exp_r), nrecs_r,
             ('%d 字节 == 目标集合' % len(diffs_r)) if full else '0 (P1 整块不动)'))

        # ⑥ MENU.IMG: 元数据区 (0 .. COMMON.PAK 数据起点 0x57400) 里只允许动
        #     ① 头 u32[0]  ② 条目表的 u32[6]=stored / u32[8]=off
        menu_diff = [i for i in range(e_pak['off']) if menu_r[i] != base_menu[i]]
        allowed_pos = set(range(0, 4))                                    # 头 u32[0]
        for c in chg:
            base = zx_lib.TAB_OFF + zx_lib.TAB_STEP * c[0]
            if c[1] == 'off':
                allowed_pos |= set(range(base + 32, base + 36))
            else:
                allowed_pos |= set(range(base + 24, base + 28))
        stray = [i for i in menu_diff if i not in allowed_pos]
        assert not stray, 'MENU.IMG 元数据区计划外字节改动 %d 处 (首个 0x%X)' \
                          % (len(stray), stray[0])
        assert bytes(menu_r[hdr2['names_start']:hdr2['names_end']]) == names0
        assert bytes(menu_r[hdr2['hash_off']:hdr2['hash_off'] + 16384]) == hash0
        # 名字区之外, 条目表里 u32[0]/u32[1] 必须逐条原值
        for i in range(len(ents)):
            base = zx_lib.TAB_OFF + zx_lib.TAB_STEP * i
            assert menu_r[base:base + 8] == base_menu[base:base + 8], i
        assert len(menu_diff) <= 4 + 4 * 683, len(menu_diff)
        P('⑥ MENU.IMG 元数据区 [0,0x57400): 计划外字节改动 0 ; 名字区 %d B / 4096 槽表 16,384 B '
          '不变 ; 每条 u32[0]/u32[1] 不变 ✓' % len(names0))
        P('   实际改动字节总数 = %d (头 u32[0] 4 B + 682 条 off 2728 B + 1 条 stored 4 B)'
          % len(menu_diff))
        info['assert1'] = dict(pair_cells=1504, ft_rects=n_rec_chk,
                               bands_moved=(n_band_skipped if full else 0),
                               old_rows_changed_px=int(oldrows_diff.sum()))
        info['assert2'] = dict(new_rows_ink=int(img_r[H_OLD:, :].sum()),
                               outside_cells=int(outside.sum()))
        info['assert3'] = dict(ct_old=len(old_ct), ct_new=len(ct_r), pak_delta=delta)
        info['assert5'] = dict(stored=ents2[e_ft['idx']]['stored'], expanded=len(exp_r),
                              nrec=nrecs_r, diffs=(len(diffs_r) if full else 0))
        info['assert6'] = dict(menu_bytes_changed=len(menu_diff), entries_off=682,
                              stored=1, names_before=len(names0))

    if a.apply_charset:
        assert full, '--apply-charset 只在 full 模式'
        import zx_charset                                             # noqa: E402
        assignment = [(c[0], c[1]) for c in info['cells']]
        zx_charset.apply_assignment(assignment, dry=a.dry_run)
        info['charset'] = dict(n=len(assignment), slot_lo=assignment[0][1],
                               slot_hi=assignment[-1][1])

    if a.prep_text:
        assert dst, '--prep-text 需要 dst'
        n = prep_text(os.path.dirname(os.path.abspath(dst)))
        info['text_in'] = n

    if a.dry_run:
        info['mode'] = info['mode'] + '-dry'
    else:
        info['iso'] = os.path.relpath(dst, REPO)
        info['sha256'] = tcslib.sha256_file(dst)
    io.open(a.report, 'w', encoding='utf-8', newline='\n').write(
        json.dumps(info, ensure_ascii=False, indent=1) + '\n')
    P('\n[rep ] → %s' % a.report)
    with io.open(os.path.join(R82, 'patch_font_%s.log' % info['mode']), 'w',
                 encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    P('[OK  ] %s 完成' % info['mode'])
    return 0


def prep_text(out_dir):
    """把"丰富版"文本表准备成注入用。

    ★ 结构列 (offset/len/…) 必须取自**当前基底盘自己的表** (work/builds/GR_ZH113b/text),
      否则注入器会报 "CSV 的 offset/len 与源盘不符"（round71 改写过 EN_SPECIAL_FEATURE.XML,
      那 25 条的长度与 r71 之前的备份不同）。
      做法 = 用当前表做骨架, 只把 `text_edited` 换成 r71 之前(丰富版)的译文;
      再把 `text_zh` 清空 ⇒ 注入器认为每行都被人工改过 ⇒ 用新 charset 全盘重编码。
    """
    import glob
    base_dir = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text')
    rich_dir = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text_backup_before_r71')
    dst_dir = os.path.join(out_dir, 'text_in')
    os.makedirs(dst_dir, exist_ok=True)

    def role(bn):
        return bn.split('_text_')[-1][:-4]

    rich = {}
    for fp in sorted(glob.glob(os.path.join(rich_dir, '*_text_*.csv'))):
        if '_view_' in os.path.basename(fp):
            continue
        r = role(os.path.basename(fp))
        with io.open(fp, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                rich[(r, row['id'])] = row.get('text_edited') or ''
    P('[text] 丰富版 (r71 之前) 载入 %d 行 (角色 %s)' % (len(rich), sorted({k[0] for k in rich})))
    n_tot = n_b1 = n_sw = 0
    for fp in sorted(glob.glob(os.path.join(base_dir, '*_text_*.csv'))):
        bn = os.path.basename(fp)
        if '_view_' in bn:
            continue
        r = role(bn)
        with io.open(fp, encoding='utf-8-sig', newline='') as f:
            rd = csv.DictReader(f)
            fields = rd.fieldnames
            rows = list(rd)
        for row in rows:
            e = rich.get((r, row['id']))
            if e is not None and e != (row.get('text_edited') or ''):
                row['text_edited'] = e
                n_sw += 1
            n_b1 += (row.get('text_edited') or '').count('{{BTN:E0B1}}')
            row['text_edited'] = (row.get('text_edited') or '').replace('{{BTN:E0B1}}', '△')
            row['text_zh'] = ''
        with io.open(os.path.join(dst_dir, bn), 'w', encoding='utf-8', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_MINIMAL)
            w.writeheader()
            for row in rows:
                w.writerow(row)
        n_tot += len(rows)
    P('[text] 注入表 → %s (%d 行, 换成丰富版译文 %d 行, {{BTN:E0B1}}→△ %d 处, text_zh 已清空)'
      % (dst_dir, n_tot, n_sw, n_b1))
    return dict(dir=os.path.relpath(dst_dir, REPO), rows=n_tot, switched=n_sw,
                b1_replaced=n_b1)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
