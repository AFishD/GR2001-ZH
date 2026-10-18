# -*- coding: utf-8 -*-
r"""zx_r83_patch.py — round83 补丁：**h 保持 512** 的 FT-记录/网格扩容盘

    python tools/re/toolbelt/zx_r83_patch.py <src.iso> <dst.iso> [--dry-run] [--report F]

设计（与 GR_ZH121 的关键差别：**一个容器尺寸字节都不动**）
  · `new_font_revised` 的 h / px_size / 段数 **全部不变**（1024x512, 0x40010, 8 段）
  · COMMON.PAK 长度不变 ⇒ **MENU.IMG 682 条 off 一个都不动**
  · FONT.RES 槽 4421 B / 展开 5942 B / nrec 224,224,96 **全部不变**（只改记录里的矩形字段）
  · ELF gate `sltiu …,0xB1` → `…,0xB4`（4 处；只用 19 个 lead 就够 1736 槽）
  · 新增 232 个字形 → 对偶码槽 1504..1735（row 24 尾 / row 25/26/27）
  · 两条活带 (452,468)(482,498) 让位 → 在自由区贪心重排（像素逐 texel 搬运）

写盘后跑七条硬断言（见 docs/REPORT_r83_ft_record_route.md）。
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
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
W, H = 1024, 512
R81 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
R82 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
R83 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r83')
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
SIMHEI = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simhei.ttf')
RW_DU = RW_DV = 0
DU, DV = RW_DU, RW_DV   # ★ 见上: 记录矩形即采样矩形
GATE_SITES_VA = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
GATE_OLD, GATE_NEW = 0xB1, 0xB4
ELF_ISO_BASE, ELF_VA_BASE = 0x93880, 0x100000
SLOT_LO, SLOT_HI = 1504, 1735
BANDS = ((452, 468), (482, 498))
MIGRATE = ['△', '键', '练', '用']
# ★★ round83 实测更正: 记录矩形 (u0,v0,u1,v1) **就是**采样矩形, 没有 +4/+2。
#    证据: 盘上 EN 带 (ASCII, 8px 步进) 在 y=453..467 / x=0.. 逐 texel 描点,
#    第 1 格 '!' 的竖杠落在 x=3 (= 窗 [0,8) 内偏移 3), 第 2 格 '"' 落在 x=10,11,13,14
#    (= 窗 [8,16) 内) ⇒ 窗 = (u0,v0)-(u1,v1)。tcslib.GLYPH_DU/DV=(4,2) 是体检容差, 不是几何。


LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ═══════════════ 字形来源 ═══════════════

def render16_simhei(ch):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(SIMHEI, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=f, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def hex_to_bitmap(hx):
    g = np.zeros((16, 16), dtype=bool)
    for y in range(16):
        v = int(hx[y], 16)
        for x in range(16):
            g[y, x] = bool((v >> (15 - x)) & 1)
    return g


def triangle16():
    g = np.zeros((16, 16), dtype=bool)

    def line(x0, y0, x1, y1):
        n = max(abs(x1 - x0), abs(y1 - y0)) * 2
        for i in range(n + 1):
            t = i / float(n)
            x = int(round(x0 + (x1 - x0) * t))
            y = int(round(y0 + (y1 - y0) * t))
            for dy in range(2):
                if 0 <= x < 16 and 0 <= y + dy < 16:
                    g[y + dy, x] = True
    line(7, 2, 2, 13)
    line(8, 2, 13, 13)
    line(2, 13, 13, 13)
    line(3, 14, 12, 14)
    return g


def load_glyphs(n_new):
    """→ [(char, bitmap16|None, 来源)] 顺序 = 槽 1504..1735"""
    gj = json.load(io.open(os.path.join(R81, 'glyphs_zh120.json'), encoding='utf-8'))
    items = {it['char']: it for it in gj['items']}
    miss = []
    with io.open(os.path.join(R82, 'rich_missing_chars.csv'), encoding='utf-8-sig',
                 newline='') as f:
        for r in csv.DictReader(f):
            miss.append(r['char'])
    out = []
    for ch in MIGRATE:
        out.append((ch, triangle16() if ch == '△' else 'copyrec', '迁移字'))
    n_fb = 0
    for ch in miss:
        if len(out) >= n_new:
            break
        if ch in MIGRATE:
            continue
        it = items.get(ch)
        if it and it.get('hex'):
            out.append((ch, hex_to_bitmap(it['hex']), 'fz16'))
        else:
            out.append((ch, render16_simhei(ch), 'simhei'))
            n_fb += 1
    P('[glyph] 就绪 %d 个 (simhei 兜底 %d: %s)'
      % (len(out), n_fb, [c for c, g, s in out if s == 'simhei']))
    assert len(out) == n_new, (len(out), n_new)
    return out


# ═══════════════ 容器像素读写 ═══════════════

class Pix:
    """引擎口径 (x,y) ↔ 容器字节（就地 nibble 写）。"""

    def __init__(self, cont, w=W):
        self.cont = bytearray(cont)
        self.segs = zx_lib.seg_table(self.cont, w)
        self.rows = {}
        for (fr, doff, nb) in self.segs:
            self.rows[fr] = (doff, nb)

    def off(self, x, y):
        best = None
        for fr, (doff, nb) in self.rows.items():
            d = y - fr
            if 0 <= d * (W // 2) + x // 2 < nb:
                best = doff + d * (W // 2) + x // 2
        assert best is not None, '像素越界/未覆盖 (%d,%d)' % (x, y)
        return best

    def get(self, x, y):
        b = self.cont[self.off(x, y)]
        return ((b >> 4) if (x & 1) else (b & 0x0F)) == 0

    def set(self, x, y, ink, empty=1):
        o = self.off(x, y)
        cur = self.cont[o]
        v = 0 if ink else empty
        self.cont[o] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)

    def clear(self, x0, y0, w, h, empty=1):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                if 0 <= x < W and 0 <= y < H:
                    try:
                        self.set(x, y, False, empty)
                    except AssertionError:
                        pass

    def blit(self, bmp, x0, y0, clear_first=True):
        h, w = bmp.shape
        if clear_first:
            self.clear(x0, y0, w, h)
        for y in range(h):
            for x in range(w):
                if bmp[y, x]:
                    self.set(x0 + x, y0 + y, True)

    def window(self, x0, y0, w, h):
        g = np.zeros((h, w), dtype=bool)
        for y in range(h):
            for x in range(w):
                g[y, x] = self.get(x0 + x, y0 + y)
        return g


# ═══════════════ 主流程 ═══════════════

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default=os.path.join(R83, 'patch_r83_report.json'))
    a = ap.parse_args(argv)
    src, dst = a.src, a.dst
    if not a.dry_run:
        assert dst, '需要 <dst.iso>'
    P('=' * 78)
    P('zx_r83_patch.py  h=512 · 容器不变 · FT 记录/网格扩容')
    P('  src = %s' % src)
    P('  dst = %s' % (dst or '(dry-run)'))
    P('=' * 78)

    iso = tcslib.Iso(src)
    names = []
    for i in range(2000):
        e = iso.img_entry(zx_lib.MENU_LBA, i)
        if e['name'].startswith('?'):
            break
        names.append(e['name'])
    e_pak = iso.img_entry(zx_lib.MENU_LBA, names.index('COMMON.PAK'))
    e_ft = iso.img_entry(zx_lib.MENU_LBA, names.index('FONT.RES'))
    hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
    names0 = zx_lib.names_region(iso, zx_lib.MENU_LBA)
    hash0 = zx_lib.hash_region(iso, zx_lib.MENU_LBA)
    pak = bytearray(iso.read(e_pak['iso_off'], e_pak['stored']))
    ft_slot = iso.read(e_ft['iso_off'], e_ft['stored'])
    P('[img] COMMON.PAK #%d off=0x%X stored=%d ; FONT.RES #%d off=0x%X stored=%d real=%d'
      % (names.index('COMMON.PAK'), e_pak['off'], e_pak['stored'],
         names.index('FONT.RES'), e_ft['off'], e_ft['stored'], e_ft['real']))
    assert (e_pak['off'], e_pak['stored']) == (0x57400, 400659)
    assert (e_ft['off'], e_ft['stored'], e_ft['real']) == (0xB9120, 4421, 7222)

    recs = tcslib.parse_pak_records(bytes(pak))
    nm, psm, aw, ah, clut, px_size, PX = recs[1]
    assert (nm, psm, aw, ah, px_size) == ('new_font_revised', 0x14, W, H, 0x40010)
    q = PX - 20 - clut
    old_ct = bytes(pak[PX:PX + px_size])
    segs_old = zx_lib.seg_table(old_ct, W)
    P('[ct ] 容器 %d B ; %d 段 %s ; ★ 尺寸/段数/h/px_size 全部不动'
      % (px_size, len(segs_old), [(s[0], s[2]) for s in segs_old]))
    assert len(segs_old) == 8 and px_size == 0x40010

    exp = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
    assert len(exp) == 5942, len(exp)
    faces, endp = zx_lib.ft_records(exp, 28)
    assert endp == 0x1620
    nrecs = [(f[0], f[1][4] * f[1][5]) for f in faces]
    assert nrecs == [('large', 224), ('default', 224), ('huge', 96)], nrecs
    P('[ft  ] 展开 5942 B ; nrec %s ; ★ 记录数与展开长度都不动' % nrecs)

    # ── 目标 busy: 网格槽 0..1735 + 留在原位的记录窗 ──
    busy = np.zeros((H, W), dtype=bool)
    CELL = {}
    for s in range(SLOT_HI + 1):
        row, col = s // 62, s % 62
        x, y = 16 * col, 2 + 16 * (row + (3 if row >= 12 else 0))
        CELL[s] = (x, y)
        busy[y:y + 16, x:x + 16] = True
    recs_all = []
    for (fn, fld, rows) in faces:
        for i, (off, r) in enumerate(rows):
            recs_all.append((fn, i, off, r[0], r[1], r[2], r[3], r[4], r[5]))
    for r in recs_all:
        fn, i, off, b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0 or (v0, v1) in BANDS:
            continue
        busy[max(0, v0 + DV):min(H, v1 + DV), max(0, u0 + DU):min(W, u1 + DU)] = True
    P('[lay] 网格槽 0..%d ; 新槽 %d..%d (%d 格, y %d..%d)'
      % (SLOT_HI, SLOT_LO, SLOT_HI, SLOT_HI - SLOT_LO + 1,
         min(CELL[s][1] for s in range(SLOT_LO, SLOT_HI + 1)),
         max(CELL[s][1] for s in range(SLOT_LO, SLOT_HI + 1)) + 16))

    # ── 两条活带搬家 ──
    def place(nw, nh):
        for y in range(DV, H - nh + 1):
            for x in range(DU, W - nw + 1):
                if not busy[y:y + nh, x:x + nw].any():
                    return x, y
        return None

    moves = {}                 # (u0,v0,u1,v1) -> (nu0,nv0,nu1,nv1)
    for band in BANDS:
        us = sorted({(r[5], r[7]) for r in recs_all
                     if (r[6], r[8]) == band and r[7] > r[5]})
        w, h = us[0][1] - us[0][0], band[1] - band[0]
        ok = 0
        for (u0, u1) in us:
            pos = place(u1 - u0, h)
            assert pos, '带 %s 的矩形 (%d,%d) 放不下' % (band, u0, u1)
            x, y = pos
            busy[y:y + h, x:x + (u1 - u0)] = True
            moves[(u0, band[0], u1, band[1])] = (x - DU, y - DV, x - DU + (u1 - u0),
                                                 y - DV + h)
            ok += 1
        P('[band] v=%s: %d 个唯一矩形 (%dx%d) 已重排' % (band, ok, w, h))
    free_after = ~busy
    P('[band] 重排后自由 = %d texel = %.1f 格 (新字占网格格 %d 个, 不额外要自由区)'
      % (int(free_after.sum()), free_after.sum() / 256.0, SLOT_HI - SLOT_LO + 1))

    # ── 目标展开态（只改带记录的矩形） ──
    tgt = bytearray(exp)
    n_chg = 0
    for r in recs_all:
        fn, i, off, b0, b1, u0, v0, u1, v1 = r
        key = (u0, v0, u1, v1)
        if key not in moves or u1 <= u0:
            continue
        nu0, nv0, nu1, nv1 = moves[key]
        assert nu0 >= 0 and nv0 >= 0 and nu1 <= W and nv1 <= H, (key, moves[key])
        struct.pack_into('<4H', tgt, off + 2, nu0, nv0, nu1, nv1)
        n_chg += 1
    P('[ft  ] 记录矩形改写 %d 条 (唯一目标 %d 个)' % (n_chg, len(moves)))
    faces2, endp2 = zx_lib.ft_records(bytes(tgt), 28)
    assert endp2 == endp and len(tgt) == len(exp)
    assert [(f[0], f[1][4] * f[1][5]) for f in faces2] == nrecs

    # ── 像素：搬运两条带 + 画 232 个新字 ──
    pix = Pix(old_ct)
    old_img = pix.window(0, 0, W, H) if False else None
    # 先读出旧带内容（按唯一矩形）
    band_src = {}
    for band in BANDS:
        us = sorted({(r[5], r[7]) for r in recs_all
                     if (r[6], r[8]) == band and r[7] > r[5]})
        for (u0, u1) in us:
            band_src[(u0, band[0], u1, band[1])] = pix.window(u0 + DU, band[0] + DV,
                                                              u1 - u0, band[1] - band[0])
    old_windows = {}
    for r in recs_all:
        fn, i, off, b0, b1, u0, v0, u1, v1 = r
        if u1 <= u0 or (v0, v1) in BANDS:
            continue
        old_windows.setdefault((u0, v0, u1, v1),
                               pix.window(u0 + DU, v0 + DV, u1 - u0, v1 - v0))
    for s in range(0, SLOT_HI + 1):
        x, y = CELL[s]
        old_windows[('cell', s)] = pix.window(x, y, 16, 16)
    n_cell_bk = SLOT_HI + 1
    P('[pix] 已备份 旧记录窗 %d 个 + 旧格 %d 个'
      % (len(old_windows) - n_cell_bk, n_cell_bk))

    # ★ 顺序很重要: 先备份 → 清旧带 → 搬带 → 画新字（新字必须在清旧带之后）
    for band in BANDS:
        for (u0, u1) in sorted({(r[5], r[7]) for r in recs_all
                                if (r[6], r[8]) == band and r[7] > r[5]}):
            pix.clear(u0 + DU, band[0] + DV, u1 - u0, band[1] - band[0])
    for key, (nu0, nv0, nu1, nv1) in moves.items():
        pix.blit(band_src[key], nu0 + DU, nv0 + DV)
    P('[pix] 两条带像素已搬到新位置并清掉旧位置')

    glyphs = load_glyphs(SLOT_HI - SLOT_LO + 1)
    for k, (ch, bmp, srctag) in enumerate(glyphs):
        s = SLOT_LO + k
        x, y = CELL[s]
        if isinstance(bmp, str) and bmp == 'copyrec':
            # 键/练/用: 从旧单字节记录的采样窗原样抠（0xB2/0xB3/0xB4 → rec 146/147/148）
            code = {0xB2: 146, 0xB3: 147, 0xB4: 148}[{'键': 0xB2, '练': 0xB3, '用': 0xB4}[ch]]
            fn, fld, rows = faces[1]
            rr = rows[code][1]
            srcbmp = pix.window(rr[2] + DU, rr[3] + DV, 16, 16)
            pix.blit(srcbmp, x, y)
        else:
            pix.blit(bmp, x, y)
    P('[pix] 232 个新字已画到 slot %d..%d' % (SLOT_LO, SLOT_HI))

    for key, (nu0, nv0, nu1, nv1) in moves.items():
        bmp2 = band_src[key]
        pix.blit(bmp2, nu0 + DU, nv0 + DV)
    P('[pix] 两条带像素已搬到新位置并清掉旧位置')

    new_ct = bytes(pix.cont)

    # ═══════ 断言 ═══════
    pix2 = Pix(new_ct)
    bad = 0
    for s in range(0, SLOT_LO):
        x, y = CELL[s]
        if not (old_windows[('cell', s)] == pix2.window(x, y, 16, 16)).all():
            bad += 1
    P('[A1] 现役 %d 个对偶格逐 texel 不变: %s (不同 %d 个)'
      % (SLOT_LO, '✓' if bad == 0 else '✗', bad))
    assert bad == 0
    for key, old in old_windows.items():
        if not isinstance(key, tuple) or key[0] == 'cell':
            continue
        u0, v0, u1, v1 = key
        new = pix2.window(u0 + DU, v0 + DV, u1 - u0, v1 - v0)
        assert (old == new).all(), key
    P('[A2] 留在原位的记录采样窗 %d 个逐 texel 不变 ✓'
      % (len([k for k in old_windows if not (isinstance(k, tuple) and k[0] == 'cell')])))
    for key, (nu0, nv0, nu1, nv1) in moves.items():
        assert (band_src[key] == pix2.window(nu0 + DU, nv0 + DV, nu1 - nu0, nv1 - nv0)).all()
    P('[A3] 搬家的 %d 条带矩形「内容等价」✓' % len(moves))
    for k, (ch, bmp, srctag) in enumerate(glyphs):
        s = SLOT_LO + k
        x, y = CELL[s]
        if isinstance(bmp, str):
            continue
        assert (bmp == pix2.window(x, y, 16, 16)).all(), ch
    P('[A4] 232 个新字格逐 texel == 模板 ✓')

    # ── FONT.RES 槽重压 ──
    cc = tcslib.lzo_compress(bytes(tgt), level=7, use_m1=True, use_m4=True)
    back, err, _ = tcslib.lzo1x_decompress(cc, out_size=len(tgt))
    assert err is None and back == bytes(tgt)
    newframe = struct.pack('<II', len(cc), len(tgt)) + cc
    P('[ft  ] 重压 %d B (原帧载荷 %d) ; 新帧 %d B ; 槽 %d B'
      % (len(cc), 1489, len(newframe), len(ft_slot)))
    assert 8 + len(cc) <= len(ft_slot), '装不下槽 (payload %d > %d)' % (8 + len(cc), len(ft_slot))
    new_slot = bytearray(ft_slot)
    new_slot[0:8] = newframe[0:8]
    new_slot[8:8 + len(cc)] = cc
    for i in range(8 + len(cc), 1497):        # 旧帧 = [8, 8+1489) 见 zx_fontres.py
        new_slot[i] = 0
    exp3 = b''.join(s[0] for s in tcslib.lzo_subs(bytes(new_slot)))
    assert len(exp3) == 5942 and exp3 == bytes(tgt)
    d2 = [i for i in range(len(exp)) if exp[i] != exp3[i]]
    tgt_set = set()
    for r in recs_all:
        fn, i, off, b0, b1, u0, v0, u1, v1 = r
        if (u0, v0, u1, v1) in moves and u1 > u0:
            tgt_set |= {off + 2 + k for k in range(8)}
    P('[A5] 回读: 展开 %d B ✓ ; 差异 %d 字节 == 目标集合: %s'
      % (len(exp3), len(d2), set(d2) <= tgt_set))
    assert set(d2) <= tgt_set

    # ── ELF gate ──
    elf_patch = []
    for va in GATE_SITES_VA:
        off = ELF_ISO_BASE + va - ELF_VA_BASE
        w0 = struct.unpack_from('<I', iso.mm, off)[0]
        imm = w0 & 0xFFFF
        assert imm == GATE_OLD, (hex(va), hex(imm))
        elf_patch.append((off, (w0 & 0xFFFF0000) | GATE_NEW))
    P('[elf] gate %d 处 0x%02X → 0x%02X: %s'
      % (len(elf_patch), GATE_OLD, GATE_NEW,
         [(hex(va), hex(off)) for va, (off, _) in zip(GATE_SITES_VA, elf_patch)]))

    if a.dry_run:
        P('[dry-run] 不写盘')
        _save(a, dict(dry=True, moves=len(moves), glyphs=len(glyphs)))
        return 0

    # ── 写盘（原盘逐字节拷贝, 只改三处） ──
    os.makedirs(os.path.dirname(os.path.abspath(dst)), exist_ok=True)
    with open(src, 'rb') as fi, open(dst, 'wb') as fo:      # 不用 shutil.copyfile
        while True:                                          # (它内部的 samefile 在本
            blk = fi.read(1 << 22)                           #  环境会抛 TypeError)
            if not blk:
                break
            fo.write(blk)
    with open(dst, 'r+b') as f:
        base = zx_lib.MENU_LBA * zx_lib.SEC
        f.seek(base + e_pak['off'] + PX)
        f.write(new_ct)
        f.seek(base + e_ft['off'])
        f.write(bytes(new_slot))
        for off, w in elf_patch:
            f.seek(off)
            f.write(struct.pack('<I', w))
    # 回读断言
    iso2 = tcslib.Iso(dst)
    assert zx_lib.names_region(iso2, zx_lib.MENU_LBA) == names0
    assert zx_lib.hash_region(iso2, zx_lib.MENU_LBA) == hash0
    pak2 = bytes(iso2.read(e_pak['iso_off'], e_pak['stored']))
    P('[A6] 回读 PAK: 长度 %d == %d ✓ ; 差异字节 %d'
      % (len(pak2), len(pak), sum(1 for i in range(len(pak)) if pak[i] != pak2[i])))
    assert len(pak2) == len(pak)
    ft2 = bytes(iso2.read(e_ft['iso_off'], e_ft['stored']))
    assert ft2 == bytes(new_slot)
    for va in GATE_SITES_VA:
        off = ELF_ISO_BASE + va - ELF_VA_BASE
        assert (struct.unpack_from('<I', iso2.mm, off)[0] & 0xFFFF) == GATE_NEW
    P('[A7] 回读 ELF gate %d/4 ✓ ; 名字区/4096 槽哈希表逐字节不变 ✓' % len(GATE_SITES_VA))
    P('[A8] ISO 尺寸 %d == %d ✓' % (os.path.getsize(dst), os.path.getsize(src)))
    assert os.path.getsize(dst) == os.path.getsize(src)
    iso2.close()
    iso.close()
    _save(a, dict(dry=False, moves=len(moves), glyphs=len(glyphs), nrec_chg=n_chg,
                  ct_bytes=len(new_ct), ft_payload=len(cc)))
    return 0


def _save(a, extra):
    d = dict(extra=extra, log=LOG)
    with io.open(a.report, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    P('[out] %s' % a.report)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
