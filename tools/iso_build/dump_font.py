# -*- coding: utf-8 -*-
r"""dump_font.py — 「字库 dump」: 把一张盘上的字库导成**一眼能看**的四件套 (只读)

用途: 每轮构筑完成后, 让人**不用跑模拟器**就能回答三个问题:
  ① 这一版的字形长什么样?               → `<版本>_font_atlas.png`
  ② 每个码位画在哪儿、有没有墨?          → `<版本>_font_ft.csv`
  ③ 本盘字符集里有哪些字、缺哪些字形?    → `<版本>_font_charset.csv`
  ④ 上面这些的汇总数字 + 各文件 sha256   → `<版本>_font_summary.json`

用法 (单跑; 构筑时由 make_build.py 自动调用, 默认开):
  python tools/iso_build/dump_font.py --iso work/builds/GR_ZH91/GR_ZH91.iso \
                                     --out work/builds/GR_ZH91/font --prefix GR_ZH91

  --scale N     PNG 放大倍数 (默认 2; 最近邻, 只为肉眼看)
  --no-png      只出 CSV/JSON, 不出 PNG (省几秒)

★ 只读: 只 mmap 读 ISO, **绝不写盘上的任何字节**。
★ 可复现: 输出里**不含时间戳**, **同一个输出目录**下对同一 ISO dump 两次, 四个文件的 sha256
  完全相同。(`summary.json` 里记了各文件的**输出路径** ⇒ 换一个输出目录写, 它的 sha256 会变;
  另外三个内容文件 (PNG / ft.csv / charset.csv) 与目录无关, 始终逐字节相同。)
★ 全部口径复用 tools/text_csv/tcslib.py 的现成实现 (字表解析 / PAK 解析 / 网格公式 /
  字形存在性检查), 本脚本**不重新逆向**任何格式:

  字表 FT   : MENU.IMG #4 `FONT.RES` (槽 @0xB9120, 存 4421 B → LZO 展开 5942 B)
              face 描述 = 14×u32; 记录 10 B `{u8 f0}{u8 f1=advance}{u16 u0}{u16 v0}{u16 u1}{u16 v1}`
              nrec = fld[4]×fld[5] (现役: 224/224/96)
  图集      : MENU.IMG #3 `COMMON.PAK` 内 `new_font_revised`, 1024×512 PSMT4 (4bpp)
              **texel 0 = 墨, 非 0 = 空** (PSMT4 每字节 2 texel: 偶 x 低 nibble)
  网格      : NCOL=62 CW=CH=16 Y0=2 SKIP_ROW=12 SKIP_ROWS=3 (对偶码走网格公式)
  ASCII/单字节: 走 FT 记录表 (idx = code-0x20), 引擎采样有 +4/+2 实测偏置 ⇒ 判墨取邻域

产出 (写进 --out 目录):
  <prefix>_font_atlas.png     图集可视化 (0=墨→黑, 非 0=空→白; 默认 2 倍最近邻放大)
  <prefix>_font_ft.csv        FT 记录表, 列:
                               face,face_name,index,code,advance,u0,v0,u1,v1,slot_x,slot_y,ink_px,has_ink
                               · face/face_name = face 序号与名 (large/default/huge)
                               · index          = 记录序号 (0..nrec-1)
                               · code           = 该记录对应的码位 = index + 0x20
                               · advance        = 记录第 2 字节 (字宽, 现役 = 8)
                               · u0,v0,u1,v1    = 记录矩形 (u 水平 / v 垂直)
                               · slot_x,slot_y  = 引擎实际采样处 (u0+4, v0+2 实测偏置)
                               · ink_px         = 记录矩形内的墨点数
                               · has_ink        = 该码位在图集里**画得出来**吗 (矩形/+4+2/±邻域三处任一有墨)
  <prefix>_font_charset.csv   字符集清单, 列:
                               char,unicode,kind,bytes_hex,slot,cell_x,cell_y,has_glyph,note
                               · kind = ascii (0x20..0x7E) / single (单字节码) /
                                        pair (对偶码) / icon (未映射控制字节 → 引擎画按键图标)
                               · slot = 网格槽号 (只对 pair 有意义)
                               · cell_x/cell_y = 字形左上角 (pair = 网格公式; 其它 = FT 记录矩形左上)
                               · has_glyph = 盘上真有字形吗 (tcslib.GlyphCache 的口径)
  <prefix>_font_summary.json  统计: face 数 / 记录数 / 字符数 / 有字形数 / 缺字形数 /
                               图集尺寸与哈希 / 各文件 sha256

退出码: 0 = 成功; 2 = 参数/装载错误 (盘不对、找不到 FONT.RES / COMMON.PAK)。
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

import tcslib                                                   # noqa: E402

try:                                        # 中文输出在重定向/管道下也要可读
    sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:                                                    # noqa: BLE001
    pass

MENU_LBA = tcslib.MENU_LBA
FT_NAME, PAK_NAME, ATLAS_REC = 'FONT.RES', 'COMMON.PAK', 'new_font_revised'
SEARCH_N = 24                       # 字表/图集都在 MENU.IMG 前 24 个条目里 (实测 #4 / #3)

# 单字节码带: 引擎的单字节码位实测落在 0xAF..0xFE (现役 76 个)。
# 这一段里**没有映射**的字节 = 引擎直接拿去画按键图标/特殊符号 (不吃字库)。
SINGLE_BAND = (0xAF, 0xFE)


# ═══════════════════════════ 小工具 ═══════════════════════════

def rel(p):
    """仓库内相对路径 (正斜杠), 写进 json 给人看。"""
    try:
        r = os.path.relpath(p, REPO)
    except ValueError:
        return p.replace('\\', '/')
    return r.replace('\\', '/') if not r.startswith('..') else p.replace('\\', '/')


def sha256_file(p):
    return tcslib.sha256_file(p)


def sha256_bytes(b):
    import hashlib
    return hashlib.sha256(b).hexdigest()


def _find_entries(iso):
    """定位 MENU.IMG 里的 FONT.RES / COMMON.PAK, 返回 (ft_e, ft_idx, pak_e, pak_idx)。"""
    ft = pak = None
    ft_i = pak_i = -1
    for i in range(SEARCH_N):
        e = iso.img_entry(MENU_LBA, i)
        if ft is None and e['name'] == FT_NAME:
            ft, ft_i = e, i
        elif pak is None and e['name'] == PAK_NAME:
            pak, pak_i = e, i
        if ft and pak:
            break
    return ft, ft_i, pak, pak_i


# ═══════════════════════════ 装载字库 ═══════════════════════════

def load_font(iso_path):
    """只读装载字库: 字表 faces + 图集像素 (字形检查用的 GlyphCache 由 dump_font() 另建)。"""
    iso = tcslib.Iso(iso_path)
    ft_e, ft_i, pak_e, pak_i = _find_entries(iso)
    if ft_e is None or pak_e is None:
        raise SystemExit('!! MENU.IMG 前 %d 个条目里找不到 %s / %s (这张盘不是本工程的盘?)'
                         % (SEARCH_N, FT_NAME, PAK_NAME))
    # ① 字表: 存的是 LZO 帧 ⇒ 先按 tcslib 的子流口径展开, 再解析 face
    ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
    if not ft_blob:
        raise SystemExit('!! FONT.RES 子流解压失败 (LZO 帧不对)')
    _head_end, faces = tcslib.parse_ft_faces(ft_blob)
    # ② 图集: COMMON.PAK 记录链里找 new_font_revised
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    atlas = None
    for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
        if nm == ATLAS_REC:
            atlas = dict(name=nm, psm=psm, w=w, h=h, clut=clut, px_size=px,
                         px_off=off, pak=pak)
            break
    iso.close()
    if atlas is None:
        raise SystemExit('!! COMMON.PAK 里找不到 %s' % ATLAS_REC)
    return dict(ft_e=ft_e, ft_idx=ft_i, ft_slot=ft_slot, ft_blob=ft_blob,
                faces=faces, pak_e=pak_e, pak_idx=pak_i, atlas=atlas)


# ═══════════════════════════ 图集 → PNG ═══════════════════════════

#   PSMT4 = 4bpp: 每字节 2 个 texel, 偶 x = 低 nibble, 奇 x = 高 nibble (与 tcslib 同口径)。
#   这里用 bytes.translate (C 速度) 逐行做两次查表, 再按 x 交错 ⇒ 1 MB 图集 ~0.3 s。
_LONIB = bytes(i & 0xF for i in range(256))
_HINIB = bytes((i >> 4) & 0xF for i in range(256))
_INK = bytes(0 if i == 0 else 255 for i in range(256))       # texel 0 = 墨 → 黑(0)


def atlas_gray(atlas):
    """图集像素 → 灰度 bytes (0=墨/黑, 255=空/白), 长度 w*h。"""
    pak, off, w, h = atlas['pak'], atlas['px_off'], atlas['w'], atlas['h']
    stride = w // 2
    buf = bytearray(w * h)
    for y in range(h):
        row = pak[off + y * stride: off + (y + 1) * stride]
        if len(row) != stride:                   # 越界: 余下按空算 (不崩)
            row = row + b'\x00' * (stride - len(row))
        base = y * w
        buf[base: base + w: 2] = row.translate(_LONIB).translate(_INK)
        buf[base + 1: base + w: 2] = row.translate(_HINIB).translate(_INK)
    return bytes(buf)


def write_atlas_png(gray, w, h, path, scale=2):
    """把二值化灰度图写成 PNG (最近邻放大 scale 倍)。只负责落盘, 不做统计。"""
    from PIL import Image
    im = Image.frombytes('L', (w, h), gray).convert('1', dither=Image.Dither.NONE)
    if scale > 1:
        im = im.resize((w * scale, h * scale), Image.NEAREST)
    im.save(path, optimize=True)
    return w, h


# ═══════════════════════════ FT 记录表 → CSV ═══════════════════════════

def _face_recs(g, recs):
    """把 GlyphCache 的「记录表」临时换成某个 face (复用它的判墨口径, 不重写逻辑)。"""
    saved = (g.recs, g.rec_nrec)
    g.recs, g.rec_nrec = recs, len(recs)
    return saved


def ft_rows(cache, faces):
    """遍历**所有 face** 的记录 ⇒ CSV 行列表。has_ink 复用 GlyphCache._check_record。"""
    ok = cache.font_ok
    out = []
    for fi, (name, fld, recs) in enumerate(faces):
        saved = _face_recs(cache, recs)
        try:
            for idx, (b0, b1, u0, v0, u1, v1) in enumerate(recs):
                code = idx + 0x20
                if ok:
                    has_ink = cache._check_record(code) is None      # 矩形 / +4+2 / ±邻域
                    ink = cache._ink(u0, v0, u1, v1) if u1 > u0 and v1 > v0 else 0
                else:
                    has_ink, ink = '', ''
                out.append(dict(face=fi, face_name=name, index=idx, code=code,
                                advance=b1, u0=u0, v0=v0, u1=u1, v1=v1,
                                slot_x=u0 + tcslib.GLYPH_DU, slot_y=v0 + tcslib.GLYPH_DV,
                                ink_px=ink, has_ink=('' if has_ink == '' else int(bool(has_ink)))))
        finally:
            cache.recs, cache.rec_nrec = saved
    return out


# ═══════════════════════════ 字符集 → CSV ═══════════════════════════

FT_COLS = ['face', 'face_name', 'index', 'code', 'advance',
           'u0', 'v0', 'u1', 'v1', 'slot_x', 'slot_y', 'ink_px', 'has_ink']
CS_COLS = ['char', 'unicode', 'kind', 'bytes_hex', 'slot',
           'cell_x', 'cell_y', 'has_glyph', 'note']


def charset_rows(cs, cache):
    """字符集全清单 (ascii / single / pair / icon), 排序固定 ⇒ 可复现。

    ★ 私有区占位字符 (按键图标) 一律按工程约定写成 ``{{BTN:XXXX}}`` 标记 ——
      CSV 里**不允许**出现私有区字符 (Excel 显示不出来, 见 toolbox 的硬门槛)。
    """
    ok = cache.font_ok
    nrec = cache.rec_nrec
    face = tcslib.FONT_FACE_DEFAULT
    rows = []

    def glyph(ch):
        """has_glyph (真/假) + 人话 note 尾巴。没装载字库时返回 ('', 说明)。"""
        if not ok:
            return '', '字库未装载, 跳过字形检查'
        r = cache.glyph_reason(ch)
        return int(r is None), ('' if r is None else r)

    # ① ASCII 0x20..0x7E —— 引擎按单字节画, 与 charset JSON 无关, 走 FT 记录表
    for b in range(0x20, 0x7F):
        ch = chr(b)
        hg, why = glyph(ch)
        note = []
        idx = b - 0x20
        if ok:
            if 0 <= idx < nrec:
                r = cache.recs[idx]
                note.append('FT rec[%d]=(%d,%d,%d,%d)' % (idx, r[2], r[3], r[4], r[5]))
            else:
                note.append('FT rec 越界 (idx=%d ≥ %d)' % (idx, nrec))
        if why:
            note.append(why + ' (ASCII 只告警: 小写字形在别的 face, 现役盘实机可读)')
        rows.append(dict(char=ch, unicode='U+%04X' % b, kind='ascii',
                         bytes_hex='%02X' % b, slot='', cell_x=(cache.recs[idx][2] if ok and 0 <= idx < nrec else ''),
                         cell_y=(cache.recs[idx][3] if ok and 0 <= idx < nrec else ''),
                         has_glyph=hg, note='; '.join(note)))

    # ② 单字节码 (含汉字 的/你 等 76 个)
    for ch, b in sorted(cs.enc_single.items(), key=lambda kv: kv[1]):
        hg, why = glyph(ch)
        idx = b - 0x20
        note = []
        if ok and 0 <= idx < nrec:
            r = cache.recs[idx]
            note.append('单字节码 0x%02X → FT rec[%d]=(%d,%d,%d,%d)' % (b, idx, r[2], r[3], r[4], r[5]))
        elif ok:
            note.append('单字节码 0x%02X 超出 FT 记录表 (idx=%d)' % (b, idx))
        if why:
            note.append(why)
        rows.append(dict(char=ch, unicode='U+%04X' % ord(ch), kind='single',
                         bytes_hex='%02X' % b, slot='',
                         cell_x=(cache.recs[idx][2] if ok and 0 <= idx < nrec else ''),
                         cell_y=(cache.recs[idx][3] if ok and 0 <= idx < nrec else ''),
                         has_glyph=hg, note='; '.join(note)))

    # ③ 对偶码 (走网格公式; lead≥0xAE 的是「死 pair」, 引擎读不了 —— 照列, 但 note 标出来)
    for ch, (b1, b2) in sorted(cs.enc_pair.items(),
                               key=lambda kv: ((kv[1][0] - 0xA1) * 94 + (kv[1][1] - 0xA1), kv[1])):
        slot = (b1 - 0xA1) * 94 + (b2 - 0xA1)
        x, y = tcslib.atlas_cell_xy(slot)
        hg, why = glyph(ch)
        note = ['网格 slot=%d (row=%d, col=%d)' % (slot, slot // tcslib.NCOL, slot % tcslib.NCOL)]
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            note.append('★死 pair: lead=0x%02X ≥ 0xAE, 引擎读成两个单字节 ⇒ 写出去是乱码 '
                        '(编码器已拒绝写出)' % b1)
        if why:
            note.append(why)
        rows.append(dict(char=ch, unicode='U+%04X' % ord(ch), kind='pair',
                         bytes_hex='%02X%02X' % (b1, b2), slot=slot, cell_x=x, cell_y=y,
                         has_glyph=hg, note='; '.join(note)))

    # ④ 未映射控制字节 (引擎直接画按键图标/特殊符号; 不吃字库)
    leads = set(v[0] for v in cs.enc_pair.values())
    for b in range(SINGLE_BAND[0], SINGLE_BAND[1] + 1):
        if b in cs.codes or b in leads:
            continue
        ch = chr(tcslib.Charset.PUA_BASE + b)
        mark = tcslib.BTN_FMT % (tcslib.Charset.PUA_BASE + b)
        rows.append(dict(char=mark, unicode='U+%04X' % (tcslib.Charset.PUA_BASE + b),
                         kind='icon', bytes_hex='%02X' % b, slot='', cell_x='', cell_y='',
                         has_glyph=1,
                         note=('引擎直接给 UV 画按键图标/特殊符号, **不吃字库**; '
                               '字节 0x%02X 在本盘字符表里没有映射 (语义未逆向, 不编造键名)'
                               % b)))
    return rows


# ═══════════════════════════ 落盘 ═══════════════════════════

def _write_csv(path, cols, rows):
    with io.open(path, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, lineterminator='\r\n')          # 工程约定: UTF-8 BOM + CRLF (Excel 友好)
        w.writerow(cols)
        for r in rows:
            w.writerow([r.get(c, '') for c in cols])


def _file_info(path):
    return dict(path=rel(path), bytes=os.path.getsize(path), sha256=sha256_file(path))


def dump_font(iso_path, out_dir, prefix, scale=2, want_png=True, iso_sha=None, verbose=True):
    """把字库 dump 到 out_dir/<prefix>_font_*; 返回写进 build_info.json 的摘要 dict。"""
    t0 = time.time()
    iso_path = os.path.abspath(iso_path)
    if not os.path.isfile(iso_path):
        raise SystemExit('!! 找不到 ISO: %s' % iso_path)
    os.makedirs(out_dir, exist_ok=True)

    font = load_font(iso_path)
    cs = tcslib.Charset()
    # ★ 字形检查一律用 tcslib 的现成检查器 (GlyphCache): 它按盘上实测口径
    #   (FT 记录表 + 网格公式 + 邻域容差) 判定「这个字画得出来吗」, 本脚本不重写这套逻辑。
    cache_iso = tcslib.Iso(iso_path)
    try:
        cache = tcslib.GlyphCache(cs, cache_iso)
        notes = list(cache.notes())
        if not cache.font_ok:
            notes.append('字库未装载 ⇒ has_glyph/has_ink 留空 (CSV 结构照出)')

        # ① 图集像素 → 二值化灰度 (墨=0/空=255) + 墨点数统计; PNG 只是它的一个视图
        gray = atlas_gray(font['atlas'])
        atlas_ink = gray.count(0)
        png_p = os.path.join(out_dir, prefix + '_font_atlas.png')
        if want_png:
            write_atlas_png(gray, font['atlas']['w'], font['atlas']['h'], png_p, scale=scale)

        # ② FT 记录表
        frows = ft_rows(cache, font['faces'])
        ft_p = os.path.join(out_dir, prefix + '_font_ft.csv')
        _write_csv(ft_p, FT_COLS, frows)

        # ③ 字符集清单
        crows = charset_rows(cs, cache)
        cs_p = os.path.join(out_dir, prefix + '_font_charset.csv')
        _write_csv(cs_p, CS_COLS, crows)
    finally:
        cache_iso.close()

    # ④ 汇总
    atlas = font['atlas']
    nrec_total = sum(len(f[2]) for f in font['faces'])
    assert len(frows) == nrec_total, 'FT 行数 %d != 记录数 %d' % (len(frows), nrec_total)
    by_kind = {}
    for r in crows:
        by_kind[r['kind']] = by_kind.get(r['kind'], 0) + 1
    n_glyph = sum(1 for r in crows if r['has_glyph'] == 1)
    n_missing = sum(1 for r in crows if r['has_glyph'] == 0)
    missing = [r['char'] for r in crows if r['has_glyph'] == 0]
    n_ft_ink = sum(1 for r in frows if r['has_ink'] == 1)
    n_ft_no = sum(1 for r in frows if r['has_ink'] == 0)
    px_used = atlas['w'] * atlas['h'] // 2            # 图集像素平面实际用的字节 (4bpp)
    px = atlas['pak'][atlas['px_off']: atlas['px_off'] + px_used]
    files = dict(ft_csv=_file_info(ft_p), charset_csv=_file_info(cs_p))
    if want_png:
        files['atlas_png'] = _file_info(png_p)

    summ = dict(
        tool='tools/iso_build/dump_font.py',
        reproducible='本文件及三个 CSV/PNG 都不含时间戳: 同一 ISO dump 两次, sha256 完全相同',
        how_to_read=dict(
            atlas_png='字库图集: 黑=有墨(字形), 白=空; 默认 2 倍最近邻放大, 一眼能看字形全貌',
            ft_csv='码位 → 图集位置 的记录表 (ASCII/单字节走这张表); has_ink=0 表示这个码位画不出来',
            charset_csv='本盘能打出的字符清单 (ascii/single/pair/icon); has_glyph=0 = 缺字形, 会画成空白',
            summary_json='本文件: 上面三样的统计与 sha256'),
        source_iso=rel(iso_path),
        source_iso_sha256=iso_sha or sha256_file(iso_path),
        font_res=dict(index=font['ft_idx'], name=FT_NAME,
                      container_offset=font['ft_e']['off'],
                      iso_offset=font['ft_e']['iso_off'], stored=font['ft_e']['stored'],
                      expanded=len(font['ft_blob']),
                      slot_sha256=sha256_bytes(font['ft_slot']),
                      expanded_sha256=sha256_bytes(font['ft_blob'])),
        atlas=dict(index=font['pak_idx'], name=PAK_NAME, record=atlas['name'],
                   container_offset=font['pak_e']['off'],
                   psm=atlas['psm'], width=atlas['w'], height=atlas['h'],
                   px_offset_in_pak=atlas['px_off'], px_size_declared=atlas['px_size'],
                   pixel_bytes_used=px_used, pixel_sha256=sha256_bytes(px),
                   ink_texels=atlas_ink, total_texels=atlas['w'] * atlas['h']),
        faces=[dict(index=i, name=f[0], records=len(f[2]),
                    nrec_field=(f[1][4] * f[1][5]), fields=list(f[1]))
               for i, f in enumerate(font['faces'])],
        counts=dict(faces=len(font['faces']), ft_records=nrec_total,
                    ft_records_with_ink=n_ft_ink, ft_records_without_ink=n_ft_no,
                    charset_rows=len(crows), by_kind=by_kind,
                    has_glyph=n_glyph, missing_glyph=n_missing),
        glyph_face_checked=dict(
            face=tcslib.FONT_FACE_DEFAULT,
            name=(font['faces'][tcslib.FONT_FACE_DEFAULT][0]
                  if len(font['faces']) > tcslib.FONT_FACE_DEFAULT else '?'),
            note='单字节/ASCII 的字形判定由 tcslib.GlyphCache 按该 face 的记录表做 '
                 '(现役盘实测引擎用的就是这个 face)'),
        grid=dict(ncol=tcslib.NCOL, cw=tcslib.CW, ch=tcslib.CH, y0=tcslib.GRID_Y0,
                  skip_row=tcslib.GRID_SKIP_ROW, skip_rows=tcslib.GRID_SKIP_ROWS,
                  formula='slot=(b1-0xA1)*94+(b2-0xA1); row=slot//ncol; col=slot%ncol; '
                          'x=4+16*col; y=2+16*(row+3*[row>=12])'),
        missing_glyph_chars=missing[:200],
        missing_glyph_truncated=(len(missing) > 200),
        png=dict(scale=scale, width=(atlas['w'] * scale if want_png else None),
                 height=(atlas['h'] * scale if want_png else None),
                 ink_pixels=atlas_ink,
                 legend='黑 = 墨 (texel 0), 白 = 空 (texel 非 0); 最近邻放大, 未加网格线'),
        files=files,
        notes=notes)
    summ_p = os.path.join(out_dir, prefix + '_font_summary.json')
    with io.open(summ_p, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(summ, f, ensure_ascii=False, indent=1)
    files['summary_json'] = _file_info(summ_p)
    summ['files'] = files                     # summary.json 的 sha256 由 build_info.json 记

    if verbose:
        print('[font] 字表 %s #%d @0x%X: 存 %d B → 展开 %d B, %d 个 face'
              % (FT_NAME, font['ft_idx'], font['ft_e']['iso_off'], font['ft_e']['stored'],
                 len(font['ft_blob']), len(font['faces'])))
        print('[font] 图集 %s #%d %s: %d×%d psm=0x%02X, 墨 %d/%d texel (%.2f%%)'
              % (PAK_NAME, font['pak_idx'], atlas['name'], atlas['w'], atlas['h'],
                 atlas['psm'], atlas_ink or 0, atlas['w'] * atlas['h'],
                 100.0 * (atlas_ink or 0) / (atlas['w'] * atlas['h'])))
        print('[font] 记录 %d 条 (有墨 %d / 无墨 %d) → %s'
              % (nrec_total, n_ft_ink, n_ft_no, rel(ft_p)))
        print('[font] 字符 %d 个 (%s) — 有字形 %d / 缺字形 %d → %s'
              % (len(crows), ' '.join('%s %d' % kv for kv in sorted(by_kind.items())),
                 n_glyph, n_missing, rel(cs_p)))
        if want_png:
            print('[font] 图集图 %d×%d (%d 倍) %.0f KB → %s'
                  % (atlas['w'] * scale, atlas['h'] * scale, scale,
                     os.path.getsize(png_p) / 1024, rel(png_p)))
        print('[font] 汇总 → %s (%.1fs)' % (rel(summ_p), time.time() - t0))
        for n in notes:
            print('[font][warn] %s' % n)
        # ★ 可复现性自检 (同一次运行里重算一遍 sha256, 只是确认写完没被改动)
        for k in ('atlas_png', 'ft_csv', 'charset_csv', 'summary_json'):
            if k in files:
                assert sha256_file(os.path.join(REPO, files[k]['path'])) == files[k]['sha256'], k
    return summ


def main():
    ap = argparse.ArgumentParser(description='字库 dump (只读): 图集 PNG + FT 记录表 + 字符集清单 + 汇总')
    ap.add_argument('--iso', required=True, help='要 dump 的 ISO (只读)')
    ap.add_argument('--out', required=True, help='输出目录 (构筑时 = work/builds/<版本>/font)')
    ap.add_argument('--prefix', default=None,
                    help='产物文件名前缀 (默认 = ISO 文件名去掉 .iso)')
    ap.add_argument('--scale', type=int, default=2, help='PNG 放大倍数 (默认 2)')
    ap.add_argument('--no-png', action='store_true', help='不出 PNG (省几秒)')
    ap.add_argument('--iso-sha', default=None, help='已知的 ISO sha256 (省一次全盘哈希)')
    a = ap.parse_args()
    prefix = a.prefix or os.path.splitext(os.path.basename(a.iso))[0]
    summ = dump_font(a.iso, a.out, prefix, scale=max(1, a.scale),
                     want_png=not a.no_png, iso_sha=a.iso_sha)
    print('[font] 四件套: %s' % ', '.join(sorted(summ['files'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
