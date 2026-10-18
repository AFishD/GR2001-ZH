# -*- coding: utf-8 -*-
r"""f364_patch.py -- 最终盘 GR_F364: 把 364 个缺字**全部**落到 h=640 的图集上

    python tools/re/toolbelt/f364_patch.py <src.iso> <dst.iso> [--dry-run] [--apply-charset]

src  = `work\builds\GR_F364\_stage640.iso`（= GR_ZH124 经 thr_patch_atlas.py 只加高 h 512→640）

本工具做的**全部**改动（逐条，其它一个字节不动）：
  ① 136 个尚未落盘的缺字 → 网格 slot **1736..1871**（紧接现役 0..1735，连续）
  ② ELF decode gate 0xB4 → **0xB5**（4 站点）—— 唯一的码位来源：20 lead × 94 = 1880 槽
     （现役 1736 + r83 的 232 已含 228 个缺字 ⇒ 还差 136 ⇒ 需要 slot ≤ 1871 < 1880 ✓）
  ③ 因为 0xB4 变成 lead，文本里 872 个**裸 0xB4 单字节码**（= 「用」）必须让位：
     就地 **0xB4 → 0x7F**（1:1，长度不变；0x7F 在全部文本容器里出现 **0 次**）
  ④ FONT.RES：3 个 face 的 **记录 95**（= 码 0x7F，原为「宽空格」矩形 (480,213)-(490,229)）
     改写成「用」的矩形/步进（取同 face 记录 148 的值）；nrec / 记录数 / 展开长度全部不变
  ⑤ charset JSON：pair_of 去「用」+ 加 136 条；codes 加「用」→0x7F（--apply-charset 才写受保护路径）

**不动**：w / psm / clut+调色板 / 记录条数 / 既有 1736 个格位 / 两条 record 带 /
名字区 / 4096 槽哈希表 / 文本内容（只换 1 个字节的编码）/ ELF 其它字节 / ISO 尺寸。
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
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

R81 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
R82 = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82')
OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_F364')
CHARSET = T.CHARSET

W, H = 1024, 640
SLOT_LO, SLOT_HI = 1736, 1871                 # 136 个新槽
NCOL = 62
GATE_OLD, GATE_NEW = 0xB4, 0xB5
ELF_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
ELF_ISO_BASE, ELF_VA_BASE = 0x93880, 0x100000
USE_CH = '用'
USE_SB_OLD = 0xB4          # 「用」的旧单字节码（r83 起 0xB4 之前仍是单字节）
SIMHEI = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts', 'simhei.ttf')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ═══════════════════════ 网格 ↔ 像素 ═══════════════════════

def cell_xy(slot):
    """引擎网格公式: row=slot/62, col=slot%62; row>=12 ⇒ row+=3; V0=16*row+2"""
    row, col = slot // NCOL, slot % NCOL
    return 16 * col, 2 + 16 * (row + (3 if row >= 12 else 0))


class Pix:
    """引擎口径 (x,y) ↔ 容器字节（就地 nibble 读写）"""

    def __init__(self, cont, w=W):
        self.cont = bytearray(cont)
        self.w = w
        self.segs = zx_lib.seg_table(bytes(cont), w)
        self.rw = w // 2

    def off(self, x, y):
        for (fr, doff, nb) in self.segs:
            d = y - fr
            if 0 <= d * self.rw + x // 2 < nb:
                return doff + d * self.rw + x // 2
        raise AssertionError('像素越界 (%d,%d)' % (x, y))

    def get(self, x, y):
        b = self.cont[self.off(x, y)]
        return ((b >> 4) if (x & 1) else (b & 0x0F)) == 0

    def set(self, x, y, ink, empty=1):
        o = self.off(x, y)
        cur = self.cont[o]
        v = 0 if ink else empty
        self.cont[o] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)

    def window(self, x0, y0, w, h):
        g = np.zeros((h, w), dtype=bool)
        for y in range(h):
            for x in range(w):
                g[y, x] = self.get(x0 + x, y0 + y)
        return g

    def blit(self, bmp, x0, y0):
        h, w = bmp.shape
        for y in range(h):
            for x in range(w):
                self.set(x0 + x, y0 + y, bool(bmp[y, x]))


# ═══════════════════════ 字形来源 ═══════════════════════

def hex_to_bitmap(hx):
    g = np.zeros((16, 16), dtype=bool)
    for y in range(16):
        v = int(hx[y], 16)
        for x in range(16):
            g[y, x] = bool((v >> (15 - x)) & 1)
    return g


def render16_simhei(ch):
    from PIL import Image, ImageDraw, ImageFont
    f = ImageFont.truetype(SIMHEI, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=f, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


# ═══════════════════════ 文本容器 ═══════════════════════

def load_conts(iso):
    out = []
    for name, spec in T.RES.items():
        for cp in spec['copies']:
            img, lba, idx, tag = cp
            e = iso.img_entry(lba, idx)
            raw = iso.read(e['iso_off'], e['stored'])
            subs = T.lzo_subs(raw)
            out.append(dict(name=name, tag=tag, img=img, lba=lba, idx=idx, entry=e,
                            slot=e['stored'], raw=bytes(raw), subs=subs,
                            blob=b''.join(s[0] for s in subs),
                            sizes=[s[2] for s in subs],
                            raws=[bytes(raw[s[3]:s[3] + 8 + s[1]]) for s in subs]))
    return out


def payload_ranges(c):
    """会**被引擎当文本渲染**的字节区间 = LANG 的条目 payload / SFXML 的文本块 + 属性值。

    ★ SFXML 的属性值（如 `<item name="M249 轻机枪" ...>`）也是**上屏文本**（标题通道），
      必须一起改写；探测证明 SFXML 的 84 个 0xB4 全在这两类区间内，结构区 0 个。
    """
    if c['name'] == 'LANG':
        ents, used = T.parse_lang(c['blob'])
        return [(e.data_off, e.data_off + e.length) for e in ents], used
    ents = T.parse_sfxml(c['blob'])
    rng = [(o, o + l) for (_k, o, l, _b) in ents]
    rng += [(o, o + len(v)) for (_k, _t, o, v) in _xml_attrs(c['blob'])]
    return rng, T.xml_tail_start(c['blob'])


def _xml_attrs(blob):
    import importlib.util
    p = os.path.join(REPO, 'tools', 'text_csv', 'inject_text_csv.py')
    if not hasattr(_xml_attrs, 'fn'):
        spec = importlib.util.spec_from_file_location('inj_attrs', p)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass
        _xml_attrs.fn = mod.parse_xml_attrs
    return _xml_attrs.fn(blob)


def find_standalone_b4(data):
    """→ [相对偏移 …]: 现役口径 (lead 0xA1..0xB3) 下的**裸 0xB4 单字节码**位置。"""
    out, i, n = [], 0, len(data)
    while i < n:
        v = data[i]
        if 0xA1 <= v < GATE_OLD and i + 1 < n and 0xA1 <= data[i + 1] < 0xFF:
            i += 2
            continue
        if v == USE_SB_OLD:
            out.append(i)
        i += 1
    return out


def reencode_use(data, pair):
    """把 data 里**裸 0xB4** 重编码成「用」的对偶 pair（逐字节等价, 渲染同一字形）。"""
    pos = find_standalone_b4(data)
    if not pos:
        return bytes(data), 0
    out = bytearray()
    prev = 0
    for i in pos:
        out += data[prev:i]
        out += bytes(pair)
        prev = i + 1
    out += data[prev:]
    return bytes(out), len(pos)


def rebuild_container(c, pair):
    """重建容器 blob: 「裸 0xB4」→ pair。**解压总长严格不变**（增长吃陈旧尾巴）。"""
    blob = c['blob']
    if c['name'] == 'SFXML':
        ranges, used = payload_ranges(c)
        ranges = [(s, min(e, used)) for (s, e) in ranges if s < used]
        used_new = bytearray()
        prev, n = 0, 0
        for (s, e) in sorted(ranges):
            if s < prev:
                raise AssertionError('重叠区间 %s @%d' % (c['tag'], s))
            used_new += blob[prev:s]
            seg, k = reencode_use(blob[s:e], pair)
            used_new += seg
            n += k
            prev = e
        used_new += blob[prev:used]
        used_new = bytes(used_new)
    else:
        ng = struct.unpack_from('<I', blob, 0)[0]
        out = bytearray(blob[0:4])
        p, n = 4, 0
        for g in range(ng):
            if g:
                out += blob[p:p + 4]
                p += 4
            cnt = struct.unpack_from('<I', blob, p)[0]
            out += blob[p:p + 4]
            p += 4
            for _i in range(cnt):
                ln = struct.unpack_from('<I', blob, p)[0]
                data = blob[p + 4:p + 4 + ln]
                nd, k = reencode_use(data, pair)
                n += k
                out += struct.pack('<I', len(nd)) + nd + blob[p + 4 + ln:p + 4 + ln + 2]
                p += 4 + ln + 2
        used = p
        used_new = bytes(out)
    assert used == (T.parse_lang(blob)[1] if c['name'] == 'LANG' else used)
    tail_keep = len(blob) - len(used_new)
    assert tail_keep >= 0, (c['tag'], len(used_new), len(blob))
    assert tail_keep <= len(blob) - used, (c['tag'], tail_keep, len(blob) - used)
    return used_new + blob[used:used + tail_keep], n


def repack(c, newblob):
    frame, q, nrep = bytearray(), 0, 0
    for k, S in enumerate(c['sizes']):
        part = newblob[q:q + S]
        q += S
        if part == c['subs'][k][0]:
            frame += c['raws'][k]
            continue
        cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
        back, err, _ = T.lzo1x_decompress(cc, out_size=S)
        assert err is None and back == part, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(cc), S) + cc
        nrep += 1
    assert q == len(newblob)
    return bytes(frame), nrep


# ═══════════════════════ 主流程 ═══════════════════════

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--apply-charset', action='store_true')
    a = ap.parse_args(argv)
    P('=' * 78)
    P('f364_patch.py  最终盘: 364 缺字全部落盘 (h=640)')
    P('  src = %s' % a.src)
    P('  dst = %s' % (a.dst or '(dry-run)'))
    P('=' * 78)

    iso = T.Iso(a.src)
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
    P('[img] MENU.IMG size %d ; COMMON.PAK off=0x%X stored=%d real=%d ; FONT.RES off=0x%X stored=%d'
      % (hdr['size'], e_pak['off'], e_pak['stored'], e_pak['real'], e_ft['off'], e_ft['stored']))
    assert e_pak['stored'] == e_pak['real'], '不变式① 前提: PAK 未压缩 ⇒ stored == real'
    assert (e_pak['off'], e_pak['stored']) == (0x57400, 466195)
    assert e_ft['off'] == 0xC9120 and e_ft['stored'] == 4421

    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    nm, psm, aw, ah, clut, px_size, PX = recs[1]
    assert (nm, psm, aw, ah, clut) == ('new_font_revised', 0x14, W, H, 1040)
    assert px_size == W * H // 2 + 16 == 0x50010, px_size
    P('[pak] rec#1 %s psm=0x%02X %dx%d clut=%d px_size=0x%X px@0x%X ; 链条 %d 条'
      % (nm, psm, aw, ah, clut, px_size, PX, len(recs)))
    ct_old = bytes(pak[PX:PX + px_size])
    segs = zx_lib.seg_table(ct_old, W)
    payload = sum(s[2] for s in segs)
    assert len(segs) == 10
    assert payload == W * H // 2 - len(segs) * 48
    P('[ct ] 不变式②: px_size == w*h/2+16 ✓ ; payload %d == w*h/2 - %d*48 ✓ ; %d 段 ; (w*h/2)%%2048=%d'
      % (payload, len(segs), len(segs), (W * H // 2) % 2048))

    # ── 现役格位（0..1735）+ 目标格位（1736..1871） ──
    ncell = 0
    while True:                                   # 网格可达上界（受 h 限制）
        x, y = cell_xy(ncell)
        if y + 16 > H:
            break
        ncell += 1
    P('[lay] 网格可达 slot 0..%d (%d 格, h=%d) ; 新槽 %d..%d (%d 个) ; 余 %d 格'
      % (ncell - 1, ncell, H, SLOT_LO, SLOT_HI, SLOT_HI - SLOT_LO + 1,
         ncell - SLOT_HI - 1))
    assert SLOT_HI < ncell, (SLOT_HI, ncell)

    pix = Pix(ct_old)
    old_cells = {s: pix.window(*cell_xy(s), 16, 16) for s in range(0, SLOT_LO)}
    free_cells = {s: int(pix.window(*cell_xy(s), 16, 16).sum())
                  for s in range(SLOT_LO, SLOT_HI + 1)}
    P('[lay] 目标槽区间当前墨量: 全 0 = %s ; 非 0 = %s'
      % (all(v == 0 for v in free_cells.values()),
         [(s, v) for s, v in free_cells.items() if v]))
    assert all(v == 0 for v in free_cells.values()), '目标格位不是空白格'

    # ── FONT.RES：★ 本方案**一个字节都不动** ──
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    exp = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, endp = zx_lib.ft_records(exp, 28)
    nrecs = [(f[0], f[1][4] * f[1][5]) for f in faces]
    assert nrecs == [('large', 224), ('default', 224), ('huge', 96)], nrecs
    new_ft = ft_slot
    n_rec_chg = 0
    P('[ft ] 展开 %d B ; endp 0x%X ; nrec %s ; ★★ FONT.RES 逐字节不变（记录 148 =「用」的原位不动）'
      % (len(exp), endp, nrecs))

    # ── 文本：裸 0xB4（「用」的旧单字节码）→ 「用」的对偶 pair ──
    cs = json.load(io.open(CHARSET, encoding='utf-8'))
    assert USE_CH in cs['pair_of'], 'charset 里没有「用」的对偶码'
    USE_PAIR = tuple(int(x) for x in cs['pair_of'][USE_CH])
    assert USE_PAIR[0] == 0xB1 and USE_PAIR[1] == 0xA4, USE_PAIR
    P('[txt] 「用」的对偶码 = 0x%02X 0x%02X（= 网格 slot %d）'
      % (USE_PAIR[0], USE_PAIR[1], T.pair_slot(*USE_PAIR)))
    conts = load_conts(iso)
    total_remap = 0
    txt_writes = []
    for c in conts:
        ranges, used = payload_ranges(c)
        nb, n = rebuild_container(c, USE_PAIR)
        total_remap += n
        assert len(nb) == len(c['blob']), '解压总长必须不变'
        # ★ 硬判据: 重建后不再有「裸 0xB4 单字节码」, 且 0xB4 只作为 trail 出现
        assert not find_standalone_b4(nb), c['tag']
        P('[txt] %-26s 区间 %d ; 改写「裸 0xB4」→ 0x%02X%02X **%d** 处 ; blob %d B 不变 ✓'
          % (c['tag'], len(ranges), USE_PAIR[0], USE_PAIR[1], n, len(nb)))
        if n == 0:
            continue
        frame, nrep = repack(c, nb)
        assert len(frame) <= c['slot'], (c['tag'], len(frame), c['slot'])
        txt_writes.append((c, frame, nb))
        P('      重压 %d 子流 → 帧 %d B / 槽 %d B (余 %d)'
          % (nrep, len(frame), c['slot'], c['slot'] - len(frame)))
    P('[txt] 合计把 %d 个「用」的旧单字节码重编码成对偶码（+%d 字节, 由陈旧尾巴吸收）'
      % (total_remap, total_remap))
    assert total_remap > 0

    # ── 136 个缺字 ──
    pair_slots = {ch: T.pair_slot(*p) for ch, p in cs['pair_of'].items()}
    miss_all = []
    with io.open(os.path.join(R82, 'rich_missing_chars.csv'), encoding='utf-8-sig',
                 newline='') as f:
        for r in csv.DictReader(f):
            miss_all.append(r['char'])
    todo = [ch for ch in miss_all if ch not in pair_slots]
    have = [ch for ch in miss_all if ch in pair_slots]
    P('[364] 目标清单 %d 个缺字 ; 已落盘 %d ; **本次落盘 %d**' % (len(miss_all), len(have), len(todo)))
    assert len(todo) == SLOT_HI - SLOT_LO + 1 == 136, len(todo)
    assert all(s <= 1735 for s in pair_slots.values()), '现役槽超出 0..1735'

    gj = json.load(io.open(os.path.join(R81, 'glyphs_zh120.json'), encoding='utf-8'))
    items = {it['char']: it for it in gj['items']}
    glyphs, n_fb = [], 0
    for ch in todo:
        it = items.get(ch)
        if it and it.get('hex'):
            glyphs.append((ch, hex_to_bitmap(it['hex']), 'fz16'))
        else:
            glyphs.append((ch, render16_simhei(ch), 'simhei'))
            n_fb += 1
    P('[gly] 模板: 方正像素16 = %d ; simhei 兜底 = %d %s'
      % (len(glyphs) - n_fb, n_fb, [c for c, _g, s in glyphs if s == 'simhei']))
    assert len(glyphs) == 136

    for k, (ch, bmp, _s) in enumerate(glyphs):
        s = SLOT_LO + k
        x, y = cell_xy(s)
        pix.blit(bmp, x, y)
    P('[pix] %d 个新字已画到 slot %d..%d (y %d..%d)'
      % (len(glyphs), SLOT_LO, SLOT_HI, cell_xy(SLOT_LO)[1], cell_xy(SLOT_HI)[1] + 16))
    new_ct = bytes(pix.cont)
    assert len(new_ct) == len(ct_old)

    # ── ELF gate ──
    elf_patch = []
    for va in ELF_SITES:
        off = ELF_ISO_BASE + va - ELF_VA_BASE
        w0 = struct.unpack_from('<I', iso.mm, off)[0]
        assert (w0 & 0xFFFF) == GATE_OLD, (hex(va), hex(w0 & 0xFFFF))
        elf_patch.append((off, (w0 & 0xFFFF0000) | GATE_NEW))
    P('[elf] decode gate 0x%02X → 0x%02X @ %s'
      % (GATE_OLD, GATE_NEW, [hex(va) for va in ELF_SITES]))
    leads = (GATE_NEW - T.LEAD_LO)
    P('[elf] 合法 lead %d 个 (0x%02X..0x%02X) ⇒ 码位空间 %d 槽 ≥ 需求 %d ⇒ 余 %d'
      % (leads, T.LEAD_LO, GATE_NEW - 1, leads * T.PAIR_STRIDE,
         SLOT_HI + 1, leads * T.PAIR_STRIDE - SLOT_HI - 1))

    # ── PAK 重建（同长） ──
    nb_ = bytearray(pak[:PX]) + bytearray(new_ct) + bytearray(pak[PX + px_size:])
    new_pak = bytes(nb_)
    assert len(new_pak) == len(pak)
    r2 = T.parse_pak_records(new_pak)
    assert (r2[1][2], r2[1][3], r2[1][5]) == (W, H, px_size)
    assert bytes(new_pak[PX - 0x43C:PX - 0x43C + 0x18]) == bytes(pak[PX - 0x43C:PX - 0x43C + 0x18])

    # ═══════ 断言 ═══════
    pix2 = Pix(new_ct)
    bad = [s for s in range(0, SLOT_LO) if not (old_cells[s] == pix2.window(*cell_xy(s), 16, 16)).all()]
    P('[A1] 现役 %d 个格位逐 texel 不变: %s (不同 %d 个)'
      % (SLOT_LO, '✓' if not bad else '✗', len(bad)))
    assert not bad
    n_rec_win = 0
    for (fn, fld, rows) in faces:
        for k, (off, r) in enumerate(rows):
            if r[4] <= r[2] or r[5] <= r[3]:
                continue
            a_ = pix.window(r[2], r[3], r[4] - r[2], r[5] - r[3])
            b_ = pix2.window(r[2], r[3], r[4] - r[2], r[5] - r[3])
            assert (a_ == b_).all(), (fn, k)
            n_rec_win += 1
    P('[A2] 全部 %d 个非空记录采样窗逐 texel 不变 ✓（新字全在 y≥%d，与记录区 y≤%d 零重叠）'
      % (n_rec_win, cell_xy(SLOT_LO)[1], max(r[5] for (_f, _fl, rows) in faces for (_o, r) in rows)))
    for k, (ch, bmp, _s) in enumerate(glyphs):
        s = SLOT_LO + k
        assert (bmp == pix2.window(*cell_xy(s), 16, 16)).all(), ch
    P('[A3] %d 个新字格逐 texel == 模板 ✓' % len(glyphs))
    assert len(new_pak) == 466195 and new_pak[:PX] == pak[:PX] and \
        new_pak[PX + px_size:] == pak[PX + px_size:]
    P('[A4] COMMON.PAK 长度 %d 不变；像素容器外的字节逐字节不变 ✓' % len(new_pak))
    P('[A5] FONT.RES 逐字节不变（展开 %d B / nrec %s / 改 %d 条记录）✓ ; 文本 %d 个「用」'
      '单字节码重编码成对偶码（blob 总长不变）✓' % (len(exp), nrecs, n_rec_chg, total_remap))

    # ── 新 charset（只加 136 条 pair_of；codes / 「用」的对偶码都不动） ──
    pairs = {ch: list(p) for ch, p in cs['pair_of'].items()}
    for k, (ch, _g, _s) in enumerate(glyphs):
        assert ch not in pairs, '新字 %r 已在 charset 里' % ch
        pairs[ch] = list(T.pair_from_slot(SLOT_LO + k))
    assert len(pairs) == len(cs['pair_of']) + 136
    codes = {k: int(v) for k, v in cs['codes'].items()}
    new_cs = dict(cs)
    new_cs['codes'] = codes
    new_cs['pair_of'] = pairs
    new_cs['_expand_f364'] = {
        'note': 'round-final(GR_F364): h 512→640; decode gate 0xB4→0xB5; '
                '136 个未落盘缺字 → 网格 slot 1736..1871（紧接现役 0..1735）; '
                '文本里 %d 个遗留的「用」单字节码 0xB4 重编码成原有的对偶码 0x%02X%02X'
                '（r83 已把「用」迁到 slot %d）; FONT.RES / codes 一字未动'
                % (total_remap, USE_PAIR[0], USE_PAIR[1], T.pair_slot(*USE_PAIR)),
        'gate_old': GATE_OLD, 'gate_new': GATE_NEW,
        'atlas_wh': [W, H], 'px_size': px_size, 'nseg': len(segs),
        'slot_lo': SLOT_LO, 'slot_hi': SLOT_HI, 'n_new': len(glyphs),
        'missing_total': len(miss_all), 'missing_already': len(have),
        'use_pair': list(USE_PAIR), 'use_pair_slot': T.pair_slot(*USE_PAIR),
        'legacy_use_bytes_reencoded': total_remap,
    }
    for ch, cp in new_cs['pair_of'].items():
        b1, b2 = cp
        assert T.LEAD_LO <= b1 < GATE_NEW and T.PAIR_TRAIL_LO <= b2 < 0xFF, (ch, cp)
    assert len(codes) == len(cs['codes']) and all(
        int(cs['codes'][k]) == v for k, v in codes.items())
    P('[cs ] pair_of %d → %d（只加 %d 条）; codes 仍 %d 条**逐字节不变** ; '
      '全部 pair lead ∈ [0x%02X,0x%02X) ✓'
      % (len(cs['pair_of']), len(pairs), len(glyphs), len(codes), T.LEAD_LO, GATE_NEW))

    if a.dry_run:
        P('[dry-run] 未写盘')
        _save(dict(dry=True, n_new=len(glyphs), remap=total_remap))
        iso.close()
        return 0

    # ═══════ 写盘 ═══════
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    with open(a.src, 'rb') as fi, open(a.dst, 'wb') as fo:
        while True:
            blk = fi.read(1 << 22)
            if not blk:
                break
            fo.write(blk)
    with open(a.dst, 'r+b') as f:
        base = zx_lib.MENU_LBA * 2048
        f.seek(base + e_pak['off'] + PX)
        f.write(new_ct)
        f.seek(base + e_ft['off'])
        f.write(bytes(new_ft) + b'\x00' * (e_ft['stored'] - len(new_ft)))
        for c, frame, _nb in txt_writes:
            f.seek(c['entry']['iso_off'])
            f.write(frame + b'\x00' * (c['slot'] - len(frame)))
        for off, w in elf_patch:
            f.seek(off)
            f.write(struct.pack('<I', w))

    # ═══════ 从盘上回读再验 ═══════
    iso2 = T.Iso(a.dst)
    assert zx_lib.names_region(iso2, zx_lib.MENU_LBA) == names0, '名字区变了'
    assert zx_lib.hash_region(iso2, zx_lib.MENU_LBA) == hash0, '4096 槽哈希表变了'
    assert zx_lib.header(iso2, zx_lib.MENU_LBA)['size'] == hdr['size']
    e2 = iso2.img_entry(zx_lib.MENU_LBA, names.index('COMMON.PAK'))
    e2f = iso2.img_entry(zx_lib.MENU_LBA, names.index('FONT.RES'))
    assert (e2['off'], e2['stored'], e2['real']) == (e_pak['off'], e_pak['stored'], e_pak['real'])
    assert e2f['off'] == e_ft['off'] and e2f['stored'] == e_ft['stored']
    pak2 = bytes(iso2.read(e2['iso_off'], e2['stored']))
    assert pak2 == new_pak, 'PAK 回读不符'
    ct2 = pak2[PX:PX + px_size]
    assert zx_lib.seg_table(ct2, W) and sum(s[2] for s in zx_lib.seg_table(ct2, W)) == payload
    assert ct2 == new_ct
    r3 = T.parse_pak_records(pak2)
    P('[A6] 回读 PAK %d B ; rec#1 %dx%d px_size=0x%X ; 容器逐字节相同 ✓'
      % (len(pak2), r3[1][2], r3[1][3], r3[1][5]))
    ft2 = bytes(iso2.read(e2f['iso_off'], e2f['stored']))
    assert ft2 == ft_slot, 'FONT.RES 槽被改了'
    P('[A7] 回读 FONT.RES: 槽 %d B **逐字节 == 源盘** ✓ ; nrec %s 不变 ✓' % (len(ft2), nrecs))
    want = dict((c['tag'], nb) for (c, _f, nb) in txt_writes)
    for c in conts:
        e_new = iso2.img_entry(c['lba'], c['idx'])
        blob2 = b''.join(s[0] for s in T.lzo_subs(bytes(iso2.read(e_new['iso_off'],
                                                                  e_new['stored']))))
        assert len(blob2) == len(c['blob']), c['tag']
        if c['tag'] in want:
            assert blob2 == want[c['tag']], '%s 回读 ≠ 目标 blob' % c['tag']
        assert not find_standalone_b4(blob2), c['tag']
        P('[A8] %-26s 回读 blob %d B 不变 ✓ ; 裸 0xB4 单字节码残留 = 0 ✓ ; 本容器重编码 %d 处'
          % (c['tag'], len(blob2), len(find_standalone_b4(c['blob']))))
    P('[A8] 3 个文本容器全部逐字节回读一致（含属性区）✓')
    for va in ELF_SITES:
        off = ELF_ISO_BASE + va - ELF_VA_BASE
        assert (struct.unpack_from('<I', iso2.mm, off)[0] & 0xFFFF) == GATE_NEW
    P('[A9] 回读 ELF gate %d/4 = 0x%02X ✓' % (len(ELF_SITES), GATE_NEW))
    assert os.path.getsize(a.dst) == os.path.getsize(a.src)
    P('[A10] ISO 尺寸 %d == 源 %d ✓' % (os.path.getsize(a.dst), os.path.getsize(a.src)))
    iso2.close()
    iso.close()

    # ═══════ charset（受保护路径，需 --apply-charset） ═══════
    csp = os.path.join(OUTDIR, 'charset_f364.json')
    with io.open(csp, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(new_cs, f, ensure_ascii=False, indent=1)
    P('[cs ] 新 charset 已写 %s' % csp)
    if a.apply_charset:
        bk = os.path.join(OUTDIR, 'charset_before_f364.json')
        if not os.path.exists(bk):
            shutil.copy2(CHARSET, bk)
            P('[cs ] 备份 %s' % bk)
        with io.open(CHARSET, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(new_cs, f, ensure_ascii=False, indent=1)
        P('[cs ] ★ 已覆盖受保护路径 %s (pair_of %d → %d)'
          % (CHARSET, len(cs['pair_of']), len(pairs)))
    else:
        P('[cs ] 未写受保护路径（加 --apply-charset 才写）')

    # 槽位表
    slots = dict((str(SLOT_LO + k), ch) for k, (ch, _g, _s) in enumerate(glyphs))
    with io.open(os.path.join(OUTDIR, 'slotmap_f364.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(slot_lo=SLOT_LO, slot_hi=SLOT_HI, n=len(glyphs),
                       source_ttf='方正像素16 / simhei(兜底 %d)' % n_fb, slots=slots),
                  f, ensure_ascii=False, indent=1)
    _save(dict(dry=False, n_new=len(glyphs), remap=total_remap, n_rec_chg=n_rec_chg,
               ft_slot=len(ft_slot), ct_bytes=len(new_ct),
               pak_bytes=len(new_pak), slots=[SLOT_LO, SLOT_HI],
               gate=[GATE_OLD, GATE_NEW], use_pair=list(USE_PAIR),
               use_pair_slot=T.pair_slot(*USE_PAIR),
               text_containers=[c['tag'] for c, _f, _n in txt_writes]))
    return 0


def _save(extra):
    d = dict(extra=extra, log=LOG)
    os.makedirs(OUTDIR, exist_ok=True)
    with io.open(os.path.join(OUTDIR, 'f364_patch_report.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'f364_patch.log'), 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    print('[out] %s' % os.path.join(OUTDIR, 'f364_patch_report.json'))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
