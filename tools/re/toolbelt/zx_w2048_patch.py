# -*- coding: utf-8 -*-
r"""zx_w2048_patch.py — **单变量探针**: 图集 W 1024 → 2048 (h 保持 512 一个字节不动)

    python tools/re/toolbelt/zx_w2048_patch.py <src.iso> <dst.iso> [--dry-run]

基底 = `work/builds/GR_ZH123/GR_ZH123.iso`（实机已证 191 张截图 ✓）
唯一变量 = `new_font_revised` 记录的 **w 字段**; 只连带改"变大所必需"的机械项:

  · 记录 +0x01C  w      : 1024 → **2048**          (h @+0x020 **不动**)
  · 记录 +0x438  px_size: 0x40010 → **0x80010**    (= 2048×512/2 + 16 = 524,304, 沿用现役
                                                    "alloc = 图像 + 16" 铁律)
  · 像素容器            : 8 段 → **16 段**, 每段 [48 B GIF 头][≤0x8000 数据] + 尾部 16 B no-op
                          ⇒ 16×48 + 523,520 + 16 = **524,304** = 0x80010 ✓
                          · 段 k 首行 = **32k**（0x8000 B = 32 行 × 1024 B/行）
                          · 行 0..510 逐字节复制现役（每行 = 旧 512 B + 512 B `0x11`）
                          · 行 511 只存前 256 B（= 旧该行 128 B + 128 B `0x11`）——与
                            现役"末段只铺 63.25 行"同构（覆盖率 511.25 行，一模一样）
  · PAK 长大 Δ = 262,144 ⇒ **同步**: PAK stored、682 条 off、MENU 声明长度、
                            ISO9660 目录长度(+PVD 卷长, 因为 89,908 B 空位不够)

**不动**: h（512）/ psm / clut+调色板 / 记录名字 / 记录条数 / FONT.RES / ELF /
charset / 文本 / 名字区 / 4096 槽哈希表 / 记录链哨兵。

写盘后跑 [A1]..[A9] 硬断言（含"旧 512 行逐字节等价"）。
"""
import argparse
import hashlib
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
SEC = 2048
W_OLD, W_NEW, H = 1024, 2048, 512
CT_OLD, CT_NEW = 0x40010, 0x80010
SEG_DATA = 0x8000                 # 每段数据上限
NSEG_OLD, NSEG_NEW = 8, 16
ROWS_NEW = SEG_DATA // (W_NEW // 2)     # = 32 行/段 (W=2048 时)
EMPTY = 0x11                      # 透明 nibble（现役容器填充口径）
TRAILER = 16
OUT = os.path.join(REPO, 'work', 'builds', 'GR_TEST_W2048')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()[:16]


# ═══════════ ISO9660 ═══════════

def pvd_vol(iso):
    pvd = iso.read(16 * SEC, SEC)
    return (struct.unpack_from('<I', pvd, 80)[0], struct.unpack_from('>I', pvd, 84)[0],
            16 * SEC + 80, 16 * SEC + 84)


def root_dir(iso):
    pvd = iso.read(16 * SEC, SEC)
    root = pvd[156:156 + 34]
    return (struct.unpack_from('<I', root, 2)[0], struct.unpack_from('<I', root, 10)[0])


def find_menu_record(iso):
    """→ (绝对 ISO 偏移, 名字, len_le, len_be)"""
    rl_lba, rl_len = root_dir(iso)
    d = iso.read(rl_lba * SEC, rl_len)
    i = 0
    while i < len(d):
        L = d[i]
        if L == 0:
            i = (i // SEC + 1) * SEC
            if i >= len(d):
                break
            continue
        rec = d[i:i + L]
        nm = rec[33:33 + rec[32]].decode('latin-1')
        if nm.upper().startswith('MENU'):
            return (rl_lba * SEC + i, nm, struct.unpack_from('<I', rec, 10)[0],
                    struct.unpack_from('>I', rec, 14)[0])
        i += L
    raise AssertionError('根目录里没有 MENU.IMG')


# ═══════════ 容器重切 ═══════════

def old_rows(ct, segs):
    """现役容器 → 每行 512 B 的行表 (行 0..510 全; 行 511 只有 128 B)。"""
    rowmap = {}
    for (first_row, doff, nb) in segs:
        nrow_full = nb // (W_OLD // 2)
        for i in range(nrow_full):
            rowmap[first_row + i] = ct[doff + i * (W_OLD // 2):doff + (i + 1) * (W_OLD // 2)]
        rest = nb - nrow_full * (W_OLD // 2)
        if rest:
            y = first_row + nrow_full
            rowmap[y] = ct[doff + nrow_full * (W_OLD // 2):doff + nb]
    return rowmap


def build_pixbuf(rowmap, target, w_new=W_NEW, h=H):
    """引擎图 (w_new × h @4bpp) 的**字节级**像素缓冲。

    长度 = `target` = 容器 − 尾部 16 B − 全部 48 B 段头（沿用现役"段头从像素区里挤出来"
    的口径 ⇒ 末行只存前 256 B，与现役"末段 63.25 行"同构）。右半 / 缺的部分填 EMPTY。
    """
    rw = w_new // 2                       # 每行字节数 (2048/2 = 1024)
    rw_old = W_OLD // 2                   # 旧行字节数 (512)
    buf = bytearray()
    for y in range(h):
        old = rowmap.get(y, b'')
        assert len(old) <= rw_old, (y, len(old))
        row = bytearray(b'\x11' * rw)
        row[0:len(old)] = old
        left = target - len(buf)
        buf += row[:left] if left < rw else row
        if len(buf) >= target:
            break
    assert len(buf) == target, (len(buf), target)
    return bytes(buf)


def build_container(pixbuf, head_tpl):
    """→ (bytes 容器, [段清单])。段 k = [48 B 头][≤0x8000 B 数据]，尾部 16 B no-op。"""
    body = bytearray()
    segs_new = []
    off = 0
    for k in range(NSEG_NEW):
        row0 = ROWS_NEW * k
        want = min(SEG_DATA, len(pixbuf) - off)
        assert want > 0, (k, off)
        head = bytearray(head_tpl)
        struct.pack_into('<I', head, 20, row0)                     # A+D 数据高 u32 = 首行
        nloop = want // 16
        assert want % 16 == 0, want
        struct.pack_into('<I', head, 32, nloop | 0x8000)            # IMAGE tag: NLOOP | EOP
        segs_new.append(dict(k=k, first_row=row0, doff=len(body) + 48,
                             nloop=nloop, nb=want, rows=want / float(W_NEW // 2)))
        body += head
        body += pixbuf[off:off + want]
        off += want
    assert off == len(pixbuf), (off, len(pixbuf))
    body += struct.pack('<II', 0x8000, 0x08000000) + b'\x00' * 8    # 尾部 no-op GIFTAG
    return bytes(body), segs_new


# ═══════════ 主流程 ═══════════

def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--grow-only', action='store_true',
                    help='★ 对照盘: 只做"PAK 长大 +Δ + 682 条 off 平移 + ISO 追加扇区", '
                         '图集 8 段 / w / px_size / h 一律不动（证明构筑机制无罪）')
    ap.add_argument('--report', default=os.path.join(OUT, 'patch_w2048_report.json'))
    a = ap.parse_args(argv)
    P('=' * 78)
    P('zx_w2048_patch.py  ★ 单变量: 图集 W 1024 → 2048 (h 保持 512)')
    P('  src = %s' % a.src)
    P('  dst = %s' % (a.dst or '(dry-run)'))
    P('=' * 78)

    iso = tcslib.Iso(a.src)
    vol_le, vol_be, vol_off_le, vol_off_be = pvd_vol(iso)
    m_abs, m_name, m_len_le, m_len_be = find_menu_record(iso)
    P('[iso] 大小 %d B = %d 扇区 ; PVD vol_space %d/%d ; MENU 记录 @0x%X len %d/%d'
      % (iso.size, iso.size // SEC, vol_le, vol_be, m_abs, m_len_le, m_len_be))
    assert vol_le == vol_be == iso.size // SEC
    assert m_len_le == m_len_be
    assert m_abs + 10 == 0x828D8, hex(m_abs)          # 与历史脚本同一站点

    hdr = zx_lib.header(iso, zx_lib.MENU_LBA)
    names0 = zx_lib.names_region(iso, zx_lib.MENU_LBA)
    hash0 = zx_lib.hash_region(iso, zx_lib.MENU_LBA)
    ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    P('[img] IMG 声明 %d ; 条目 %d ; COMMON.PAK #%d off=0x%X stored=%d ; FONT.RES #%d off=0x%X stored=%d'
      % (hdr['size'], len(ents), e_pak['idx'], e_pak['off'], e_pak['stored'],
         e_ft['idx'], e_ft['off'], e_ft['stored']))
    assert hdr['size'] == m_len_le == 58300882, hdr['size']
    assert (e_pak['off'], e_pak['stored']) == (0x57400, 400659)
    assert (e_ft['off'], e_ft['stored'], e_ft['real']) == (0xB9120, 4421, 7222)
    old_end = e_pak['off'] + e_pak['stored']
    last_end = max(e['off'] + e['stored'] for e in ents)
    P('[img] PAK end=0x%X ; 最后条目 end=%d ; 声明尾料 %d B'
      % (old_end, last_end, hdr['size'] - last_end))

    # ── PAK / 记录 ──
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = tcslib.parse_pak_records(pak)
    assert len(recs) == 4 and recs[1][0] == 'new_font_revised'
    nm, psm, aw, ah, clut, px_size, px_off = recs[1]
    assert (psm, aw, ah, clut, px_size) == (0x14, W_OLD, H, 1040, CT_OLD)
    assert px_off == 0x146D
    rec_off = px_off - 0x43C                                   # = 0x1031 ✓
    P('[pak] %d B ; rec#1 @PAK+0x%X: psm=0x%02X %dx%d clut=%d px_size=0x%X 容器@0x%X'
      % (len(pak), rec_off, psm, aw, ah, clut, px_size, px_off))
    P('[pak] 其它记录: %s' % [(r[0], hex(r[6])) for r in (recs[0], recs[2], recs[3])])
    assert struct.unpack_from('<I', pak, px_off - 4)[0] == CT_OLD   # px_size 字段 = 0x438
    assert struct.unpack_from('<I', pak, rec_off + 0x20)[0] == H    # h 字段
    h_bytes = bytes(pak[rec_off + 0x20:rec_off + 0x24])
    pal_bytes = bytes(pak[rec_off + 0x28:rec_off + 0x438])
    name_bytes = bytes(pak[rec_off:rec_off + 0x18])

    # ── 现役容器 ──
    ct_old = bytes(pak[px_off:px_off + CT_OLD])
    segs_old = zx_lib.seg_table(ct_old, W_OLD)
    P('[ct ] 现役容器 %d B ; %d 段 %s' % (len(ct_old), len(segs_old),
                                        [(s[0], s[2]) for s in segs_old]))
    assert len(segs_old) == NSEG_OLD and segs_old[-1][2] == 32384
    delta = CT_NEW - CT_OLD

    if a.grow_only:
        ct_new, segs_new = ct_old, None
        P('[ct ] ★ --grow-only 对照: 容器/px_size/w/h **一律不动**（%d B / %d 段）'
          % (len(ct_old), len(segs_old)))
    else:
        rowmap = old_rows(ct_old, segs_old)
        assert len(rowmap) == 512, len(rowmap)
        assert len(rowmap[511]) == 128
        pix_target = CT_NEW - TRAILER - NSEG_NEW * 48
        pixbuf = build_pixbuf(rowmap, pix_target)
        P('[pix] 新像素缓冲 %d B (容器 %d − 尾 16 − %d×48 段头) = %.2f 行 × %d B'
          % (len(pixbuf), CT_NEW, NSEG_NEW, len(pixbuf) / float(W_NEW // 2), W_NEW // 2))
        tail_zone = pixbuf[500 * 1024:]
        P('[pix] 行 500.. 尾部区 %d B: 0x11 × %d, 0x00 × %d, 其它 × %d（现役空区口径核对）'
          % (len(tail_zone), tail_zone.count(0x11), tail_zone.count(0x00),
             sum(1 for b in tail_zone if b not in (0x11, 0x00))))
        head_tpl = ct_old[0:48]
        ct_new, segs_new = build_container(pixbuf, head_tpl)
        P('[ct ] 新容器 %d B = 0x%X ; %d 段 ; 末段 %d B (%.2f 行)'
          % (len(ct_new), len(ct_new), len(segs_new), segs_new[-1]['nb'],
             segs_new[-1]['rows']))
        for s in segs_new:
            P('       seg%-2d 首行=%-4d nloop=0x%X nb=%-6d' % (s['k'], s['first_row'],
                                                               s['nloop'], s['nb']))
        assert len(ct_new) == CT_NEW == NSEG_NEW * 48 + len(pixbuf) + TRAILER
        segs_chk = zx_lib.seg_table(ct_new, W_NEW)
        assert [(s[0], s[2]) for s in segs_chk] == [(s['first_row'], s['nb'])
                                                    for s in segs_new]

    # ── 新 PAK ──
    if a.grow_only:
        # ★ 长大发生在记录链结束哨兵 (0x63) 之后 ⇒ 记录链自身一字不动
        new_pak = bytes(pak) + b'\x00' * delta
    else:
        nb_ = bytearray(pak[:px_off])
        struct.pack_into('<I', nb_, rec_off + 0x01C, W_NEW)          # ★ 唯一变量
        struct.pack_into('<I', nb_, px_off - 4, CT_NEW)              # px_size
        nb_ += ct_new
        nb_ += pak[px_off + CT_OLD:]
        new_pak = bytes(nb_)
    P('[pak] PAK %d → %d B (Δ %+d%s)' % (len(pak), len(new_pak), len(new_pak) - len(pak),
                                        ' = 容器增量' if not a.grow_only else ' 纯追加零'))
    assert len(new_pak) - len(pak) == delta == 262144
    recs2 = tcslib.parse_pak_records(new_pak)
    assert [r[0] for r in recs2] == [r[0] for r in recs]
    if a.grow_only:
        assert [r[6] for r in recs2] == [r[6] for r in recs], '对照盘记录链不该动'
        assert bytes(new_pak[:len(pak)]) == pak
    else:
        assert (recs2[1][2], recs2[1][3], recs2[1][5]) == (W_NEW, H, CT_NEW)
        assert recs2[2][6] == recs[2][6] + delta and recs2[3][6] == recs[3][6] + delta
    assert bytes(new_pak[rec_off + 0x20:rec_off + 0x24]) == h_bytes, '★ h 被改动了!'
    assert bytes(new_pak[rec_off + 0x28:rec_off + 0x438]) == pal_bytes
    assert bytes(new_pak[rec_off:rec_off + 0x18]) == name_bytes
    P('[pak] 回读 %s' % [(r[0], r[2], r[3], hex(r[5])) for r in recs2])
    P('[pak] ★ h 字段 4 字节逐字节不变 %s ; 调色板 1040 B 不变 ✓ ; 名字不变 ✓'
      % h_bytes.hex(' '))

    # ── 新 MENU.IMG ──
    phys = min(vol_le * SEC - zx_lib.MENU_LBA * SEC, hdr['size'])
    old_phys = bytes(iso.read(zx_lib.MENU_LBA * SEC,
                              vol_le * SEC - zx_lib.MENU_LBA * SEC))
    need = last_end + delta
    new_size = ((need + SEC - 1) // SEC) * SEC
    new_vol = zx_lib.MENU_LBA + new_size // SEC
    P('[menu] 旧声明 %d ; 新 need %d ⇒ 新声明 %d (%d 扇区, 扇区对齐)'
      % (hdr['size'], need, new_size, new_size // SEC))
    P('[menu] ★ 盘尾空位只到 %d 扇区（%d B）⇒ ISO 必须从 %d 长到 %d 扇区 (Δ %+d 扇区 = %+d B)'
      % (vol_le, phys, vol_le, new_vol, new_vol - vol_le, (new_vol - vol_le) * SEC))
    new_menu = bytearray(old_phys)
    new_menu += b'\x00' * (new_size - len(new_menu))
    new_menu[e_pak['off']:e_pak['off'] + len(new_pak)] = new_pak
    tail = bytes(iso.read(e_pak['iso_off'] + e_pak['stored'], last_end - old_end))
    new_menu[old_end + delta:last_end + delta] = tail
    struct.pack_into('<I', new_menu, 0, new_size)
    n_off = 0
    for e in ents:
        if e['off'] >= e_ft['off']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             e['off'] + delta)
            n_off += 1
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
    P('[menu] 条目表改动: off %d 条 (+%d) + stored 1 条' % (n_off, delta))
    assert n_off == 682, n_off
    assert bytes(new_menu[hdr['names_start']:hdr['names_end']]) == names0
    assert bytes(new_menu[hdr['hash_off']:hdr['hash_off'] + 16384]) == hash0
    # ★ PAK 之前的元数据: 只允许 IMG 头 size(=0) 与条目表的 off/stored 两处改动
    exp_meta = bytearray(old_phys[0:e_pak['off']])
    struct.pack_into('<I', exp_meta, 0, new_size)
    for e in ents:
        if e['off'] >= e_ft['off']:
            struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             e['off'] + delta)
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
    dmeta = [i for i in range(e_pak['off']) if new_menu[i] != old_phys[i]]
    assert bytes(new_menu[0:e_pak['off']]) == bytes(exp_meta), '★ 元数据出现计划外改动'
    P('[menu] PAK 之前元数据 0x%X B: 计划外改动 0 ; 实际差异 %d 字节 '
      '(size 4 + 条目表 off %d×4 + stored 4) ; 名字区 %d B / 4096 槽表 16,384 B 逐字节不变 ✓'
      % (e_pak['off'], len(dmeta), n_off, len(names0)))

    if a.dry_run:
        P('[dry ] 不写盘')
        _save(a, dict(dry=True, delta=delta, new_size=new_size, new_vol=new_vol))
        iso.close()
        return 0

    # ── 写盘 ──
    os.makedirs(os.path.dirname(os.path.abspath(a.dst)), exist_ok=True)
    with open(a.src, 'rb') as fi, open(a.dst, 'wb') as fo:
        while True:
            blk = fi.read(1 << 22)
            if not blk:
                break
            fo.write(blk)
        fo.write(b'\x00' * ((new_vol - vol_le) * SEC))          # ★ 追加扇区
    with open(a.dst, 'r+b') as f:
        f.seek(zx_lib.MENU_LBA * SEC)
        f.write(bytes(new_menu))
        f.seek(m_abs + 10)
        f.write(struct.pack('<I', new_size) + struct.pack('>I', new_size))
        f.seek(vol_off_le)
        f.write(struct.pack('<I', new_vol) + struct.pack('>I', new_vol))
    P('[out] %s (%d B = %d 扇区)' % (a.dst, os.path.getsize(a.dst), os.path.getsize(a.dst) // SEC))

    # ── 回读硬断言 ──
    iso2 = tcslib.Iso(a.dst)
    hdr2 = zx_lib.header(iso2, zx_lib.MENU_LBA)
    ents2 = zx_lib.entries(iso2, zx_lib.MENU_LBA)
    e2_pak = ents2[e_pak['idx']]
    e2_ft = ents2[e_ft['idx']]
    pak2 = bytes(iso2.read(e2_pak['iso_off'], e2_pak['stored']))
    r2 = tcslib.parse_pak_records(pak2)
    P('[A1] 回读 PAK %d B ; rec#1 %s ; px_size=0x%X'
      % (len(pak2), (r2[1][2], r2[1][3], r2[1][5]), r2[1][5]))
    assert len(pak2) == len(new_pak) and pak2 == new_pak
    if a.grow_only:
        assert (r2[1][2], r2[1][3], r2[1][5]) == (W_OLD, H, CT_OLD)
    else:
        assert (r2[1][2], r2[1][3], r2[1][5]) == (W_NEW, H, CT_NEW)
    ct2 = pak2[r2[1][6]:r2[1][6] + r2[1][5]]
    segs2 = zx_lib.seg_table(ct2, r2[1][2])
    if a.grow_only:
        assert ct2 == ct_old and len(segs2) == NSEG_OLD
    else:
        assert [(s[0], s[2]) for s in segs2] == [(s['first_row'], s['nb'])
                                                 for s in segs_new]
    P('[A2] 回读容器 %d B ; %d 段 首行 %s' % (len(ct2), len(segs2), [s[0] for s in segs2]))

    if a.grow_only:
        P('[A3] ★ --grow-only: 容器逐字节 == 现役 ⇒ 旧行等价性平凡成立 ✓')
        assert ct2 == ct_old
    else:
        # ★ 旧 512 行逐字节等价（引擎口径, x < 1024 部分）
        rw_new = W_NEW // 2
        bad = 0
        n_row = 0
        for (first_row, doff, nb) in segs2:
            nrow_full = nb // rw_new
            for i in range(nrow_full):
                y = first_row + i
                new_row = ct2[doff + i * rw_new:doff + (i + 1) * rw_new]
                old_row = rowmap.get(y, b'')
                if new_row[0:len(old_row)] != old_row:
                    bad += 1
                if any(b != EMPTY for b in new_row[len(old_row):]):
                    bad += 1
                n_row += 1
        P('[A3] ★ %d 个整行: x<1024 部分逐字节 == 现役 ; x>=1024 全 0x%02X : %s (不符 %d)'
          % (n_row, EMPTY, '✓' if bad == 0 else '✗', bad))
        assert bad == 0
    assert bytes(pak2[rec_off + 0x20:rec_off + 0x24]) == h_bytes
    assert bytes(pak2[rec_off + 0x28:rec_off + 0x438]) == pal_bytes
    P('[A4] ★ h 字段 %s 逐字节不变 ; 调色板 1040 B 不变 ✓' % h_bytes.hex(' '))

    ft2 = bytes(iso2.read(e2_ft['iso_off'], e2_ft['stored']))
    ft1 = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    assert ft2 == ft1 and e2_ft['off'] == e_ft['off'] + delta
    P('[A5] FONT.RES 槽 4421 B 逐字节不变, off 0x%X → 0x%X (+%d) ✓'
      % (e_ft['off'], e2_ft['off'], delta))
    tail2 = bytes(iso2.read(e_pak['iso_off'] + len(pak2), last_end + delta
                            - (old_end + delta)))
    assert tail2 == tail
    P('[A6] PAK 之后 %d B（13 B 间隙 + FONT.RES..EN_STRINGS.TXT）逐字节平移不变 ✓'
      % len(tail2))
    assert zx_lib.names_region(iso2, zx_lib.MENU_LBA) == names0
    assert zx_lib.hash_region(iso2, zx_lib.MENU_LBA) == hash0
    P('[A7] 名字区 / 4096 槽哈希表逐字节不变 ✓ ; IMG 声明 %d == %d ✓'
      % (hdr2['size'], new_size))
    assert hdr2['size'] == new_size
    v2_le, v2_be, _, _ = pvd_vol(iso2)
    m2 = find_menu_record(iso2)
    assert (v2_le, v2_be) == (new_vol, new_vol)
    assert m2[2] == m2[3] == new_size and m2[0] == m_abs
    assert os.path.getsize(a.dst) == new_vol * SEC
    P('[A8] ISO9660: MENU.IMG len %d/%d @0x%X ✓ ; PVD vol_space %d ✓ ; ISO %d B ✓'
      % (m2[2], m2[3], m2[0], v2_le, os.path.getsize(a.dst)))

    # ★ 逐字节差异区段 (src vs dst)
    ranges = diff_ranges(a.src, a.dst, 1 << 22)
    P('[A9] 逐字节差异区段 %d 个:' % len(ranges))
    for (o, n) in ranges:
        P('       0x%09X .. 0x%09X  (%d B = %.1f KB)' % (o, o + n, n, n / 1024.0))
    iso2.close()
    iso.close()
    _save(a, dict(dry=False, delta=delta, ct_old=CT_OLD, ct_new=CT_NEW,
                  pak_old=len(pak), pak_new=len(new_pak), menu_old=hdr['size'],
                  menu_new=new_size, iso_old=vol_le * SEC, iso_new=new_vol * SEC,
                  vol_old=vol_le, vol_new=new_vol, last_end_old=last_end,
                  last_end_new=last_end + delta, n_off_shift=n_off,
                  diff_ranges=[dict(off=o, len=n) for (o, n) in ranges],
                  offsets=dict(w_field=struct.unpack_from('<I', pak, rec_off + 0x1C)[0],
                               px_size_field_iso=e_pak['iso_off'] + px_off - 4,
                               w_field_iso=e_pak['iso_off'] + rec_off + 0x1C,
                               h_field_iso=e_pak['iso_off'] + rec_off + 0x20,
                               menu_len_iso=m_abs + 10, pvd_vol_iso=vol_off_le)))
    return 0


def diff_ranges(p1, p2, blk=1 << 22):
    """两块流式对比 → 连续差异区段 [(off, len)]（numpy 分块, 跨块合并）。"""
    import numpy as np
    out = []
    off = 0
    with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
        while True:
            b1 = f1.read(blk)
            b2 = f2.read(blk)
            if not b1 and not b2:
                break
            n = min(len(b1), len(b2))
            if n:
                a1 = np.frombuffer(b1[:n], dtype=np.uint8)
                a2 = np.frombuffer(b2[:n], dtype=np.uint8)
                ne = np.flatnonzero(a1 != a2)
                if ne.size:
                    brk = np.flatnonzero(np.diff(ne) > 1)
                    starts = np.concatenate(([0], brk + 1))
                    ends = np.concatenate((brk, [ne.size - 1]))
                    for s, e in zip(starts, ends):
                        o = off + int(ne[s])
                        ln = int(ne[e]) - int(ne[s]) + 1
                        if out and out[-1][0] + out[-1][1] == o:
                            out[-1] = (out[-1][0], out[-1][1] + ln)
                        else:
                            out.append((o, ln))
            if len(b1) != len(b2):
                o = off + n
                ln = abs(len(b1) - len(b2))
                if out and out[-1][0] + out[-1][1] == o:
                    out[-1] = (out[-1][0], out[-1][1] + ln)
                else:
                    out.append((o, ln))
            off += max(len(b1), len(b2))
    return out


def _save(a, extra):
    d = dict(extra=extra, log=LOG)
    os.makedirs(os.path.dirname(os.path.abspath(a.report)), exist_ok=True)
    with io.open(a.report, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    with io.open(os.path.splitext(a.report)[0] + '.log', 'w', encoding='utf-8',
                 newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    P('[out] %s' % a.report)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
