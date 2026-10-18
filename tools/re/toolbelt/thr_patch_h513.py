# -*- coding: utf-8 -*-
r"""thr_patch_h513.py -- round86 单变量探针: 图集 **h 512 → 513**（w / psm / clut 一字不动）

    python tools/re/toolbelt/thr_patch_h513.py <src.iso> <dst.iso> [--variant minimal|full] [--dry-run]

基底 = `work\builds\GR_ZH124\GR_ZH124.iso`（实机已证 ✓ 191 截图）

★ 唯一变量 = `new_font_revised` 记录的 **h 字段**（+0x020）512 → 513。
  连带项只有"h 变大所必需"的机械项:

  · 记录 +0x438  px_size  : 0x40010 → 0x40240 (variant=minimal) / 0x403C0 (variant=full)
  · 像素容器              : 9 段（第 9 段 = 1 行 512 B，SSAY=512，NLOOP=32）
      minimal: **前 262,144 B 与现役逐字节相同**（严格追加：新段头 48 + 512 B 0x11 + 尾 tag 16）
               ⇒ 262,144 + 48 + 512 + 16 = 262,720 = 0x40240，Δ = **+560 B**
      full   : seg7 补满 64 行（+384 B）+ 第 9 段 1 行 ⇒ 0x403C0，Δ = +944 B
  · COMMON.PAK stored      : 400,659 → +Δ
  · COMMON.PAK **real**    : ★ round86 关键: 原盘 stored==real==400,659（未压缩）。
                             若只改 stored 不改 real（= 历史探针盘的做法），条目表就变成
                             stored > real。实测: 读流会在 **PAK+real(=400,659)** 处停死。
                             `--real-mode skip` 复现该 bug，`--real-mode fixed`(默认) 同步 real。
  · 条目表 682 条 off      : +Δ（off ≥ FONT.RES off 的条目）
  · MENU.IMG 声明长度 / ISO9660 / PVD: **不需要动**（Δ 远小于 61,236 B 尾料裕量）

**不动**: w / psm / clut+调色板 1040 B / 记录名字 / 记录条数 / FONT.RES / ELF / charset /
文本 / 名字区 / **IMG +0x20 的 4096 槽哈希表** / 记录链哨兵 / ISO 长度。

写盘后跑 [A1]..[A10] 硬断言 + 全盘逐字节差异区段。
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
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..', '..', 'tools', 'text_csv')))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import zx_lib                                                        # noqa: E402
import tcslib                                                        # noqa: E402

REPO = zx_lib.REPO
SEC = 2048
MENU_LBA = tcslib.MENU_LBA
W = 1024
H_OLD, H_NEW = 512, 513
CT_OLD = 0x40010                     # 262,160
ROW_BYTES = W // 2                   # 512 B/行 (4bpp)
EMPTY = 0x11
TAIL_BYTES = 16                      # 尾部 no-op GIF tag
SEG_HEAD = 48                        # [PT 16][A+D 16][IMAGE 16]
OUT = os.path.join(REPO, 'work', 'builds', 'GR_THR86')
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()[:16]


# ═══════════ 变体定义 ═══════════

def build_container(ct_old, variant):
    """→ (new_ct, desc)。9 段，第 9 段放 1 行 (512 B)。"""
    tail = bytes(ct_old[len(ct_old) - TAIL_BYTES:])
    assert tail[:4] == b'\x00\x80\x00\x00', tail.hex()          # no-op tag NLOOP=0 EOP=1
    head = bytearray(ct_old[0:SEG_HEAD])                        # PT + A+D + IMAGE 模板
    assert head[0:8] == b'\x01\x00\x00\x00\x00\x00\x00\x10', head.hex()
    # A+D: SSAX@+16 = 0 ; SSAY@+20 = 512 ; u64@+24 = 0x52
    struct.pack_into('<I', head, 16, 0)
    struct.pack_into('<I', head, 20, H_OLD)                     # = 512 首行
    struct.pack_into('<Q', head, 24, 0x52)
    # IMAGE tag @+32: NLOOP = 512/16 = 32, EOP=1, FLG=2
    struct.pack_into('<I', head, 32, (ROW_BYTES // 16) | 0x8000)
    struct.pack_into('<I', head, 36, 0x08000000)

    if variant == 'minimal':
        prefix = bytes(ct_old[0:0x40000])                        # 严格：现役前 262,144 B
        note = '现役前 0x40000 B 逐字节保留(含 8 段+seg7 63.25 行)'
    else:
        # full: seg7 由 32,384 → 32,768 B (补 384 B 0x11)，其后接第 9 段
        seg7_head = ct_old[0x38150:0x38180]
        assert struct.unpack_from('<I', seg7_head, 32)[0] == 2024 | 0x8000
        s7 = bytearray(seg7_head)
        struct.pack_into('<I', s7, 32, 2048 | 0x8000)            # NLOOP 2024 -> 2048
        prefix = (bytes(ct_old[0:0x38150]) + bytes(s7)
                  + bytes(ct_old[0x38180:0x40000]) + b'\x11' * (0x8000 - 0x7E80))
        assert len(prefix) == 0x38150 + 48 + 0x8000
        note = 'seg7 补满 64 行 (+384 B) 后接第 9 段'
    body = bytes(head) + b'\x11' * ROW_BYTES + tail
    return prefix + body, note


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst', nargs='?')
    ap.add_argument('--variant', default='minimal', choices=['minimal', 'full'])
    ap.add_argument('--real-mode', default='fixed', choices=['fixed', 'skip'],
                    help='fixed=同步 COMMON.PAK 条目 +0x01C 的 real(=stored); '
                         'skip=历史探针盘做法(只改 stored，复现停摆)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--report', default=os.path.join(OUT, 'patch_h513_%s_report.json'))
    a = ap.parse_args(argv)
    if '%s' in a.report:
        a.report = a.report % a.variant
    P('=' * 78)
    P('thr_patch_h513.py  ★ 单变量: 图集 h 512 → 513 (w/psm/clut 不动) ; variant=%s' % a.variant)
    P('  src = %s' % a.src)
    P('  dst = %s' % (a.dst or '(dry-run)'))
    P('=' * 78)

    iso = tcslib.Iso(a.src)
    hdr = zx_lib.header(iso, MENU_LBA)
    names0 = zx_lib.names_region(iso, MENU_LBA)
    hash0 = zx_lib.hash_region(iso, MENU_LBA)
    ents = zx_lib.entries(iso, MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    P('[img] ISO %d B = %d 扇区 ; IMG 声明 %d ; 条目 %d ; names %d..%d ; hash@0x%X'
      % (iso.size, iso.size // SEC, hdr['size'], len(ents), hdr['names_start'],
         hdr['names_end'], hdr['hash_off']))
    P('[img] COMMON.PAK #%d off=0x%X stored=%d ; FONT.RES #%d off=0x%X stored=%d'
      % (e_pak['idx'], e_pak['off'], e_pak['stored'], e_ft['idx'], e_ft['off'], e_ft['stored']))
    assert iso.size == 804768 * SEC, iso.size
    assert hdr['size'] == 58300882, hdr['size']
    assert (e_pak['off'], e_pak['stored']) == (0x57400, 400659)
    assert (e_ft['off'], e_ft['stored'], e_ft['real']) == (0xB9120, 4421, 7222)

    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = tcslib.parse_pak_records(pak)
    assert len(recs) == 4 and recs[1][0] == 'new_font_revised'
    nm, psm, aw, ah, clut, px_size, px_off = recs[1]
    assert (psm, aw, ah, clut, px_size) == (0x14, W, H_OLD, 1040, CT_OLD)
    assert px_off == 0x146D
    rec_off = px_off - 0x43C                                       # 0x1031
    P('[pak] PAK %d B ; rec#1 @PAK+0x%X psm=0x%02X %dx%d clut=%d px_size=0x%X'
      % (len(pak), rec_off, psm, aw, ah, clut, px_size))
    h_bytes = bytes(pak[rec_off + 0x20:rec_off + 0x24])
    w_bytes = bytes(pak[rec_off + 0x1C:rec_off + 0x20])
    pal_bytes = bytes(pak[rec_off + 0x28:rec_off + 0x438])
    name_bytes = bytes(pak[rec_off:rec_off + 0x18])
    P('[pak] w=%s h=%s 调色板 %d B' % (w_bytes.hex(' '), h_bytes.hex(' '), len(pal_bytes)))

    ct_old = bytes(pak[px_off:px_off + CT_OLD])
    ct_new, note = build_container(ct_old, a.variant)
    CT_NEW = len(ct_new)
    delta = CT_NEW - CT_OLD
    P('[ct ] %s' % note)
    P('[ct ] 容器 %d (0x%X) → %d (0x%X)  Δ = **%+d B**'
      % (CT_OLD, CT_OLD, CT_NEW, CT_NEW, delta))
    segs = tcslib.atlas_container_segments(ct_new, W // 2)
    real = [s for s in segs if s[2] > 0]
    P('[ct ] 段表 %d 段: %s' % (len(real), [(s[0], s[1], s[2]) for s in real]))
    assert len(real) == 9, len(real)
    assert real[-1][0] == H_OLD and real[-1][2] == ROW_BYTES
    exp_px = (8 * 0x8000 if a.variant == 'full' else 7 * 0x8000 + 0x7E80) + ROW_BYTES
    assert sum(s[2] for s in real) == exp_px, (sum(s[2] for s in real), exp_px)
    keep = 0x40000 if a.variant == 'minimal' else 0x38150 + 48 + 0x8000
    assert ct_new[:keep] == ct_old[:keep], '★ 现役容器前缀被改动'
    assert delta < 61236, 'Δ 超出 IMG 尾料裕量, 本脚本不支持加长 ISO'

    # ── 新 PAK ──
    nb = bytearray(pak[:px_off])
    struct.pack_into('<I', nb, rec_off + 0x20, H_NEW)              # ★ 唯一变量
    struct.pack_into('<I', nb, px_off - 4, CT_NEW)                 # px_size 机械项
    nb += ct_new
    nb += pak[px_off + CT_OLD:]
    new_pak = bytes(nb)
    assert len(new_pak) - len(pak) == delta
    r2 = tcslib.parse_pak_records(new_pak)
    assert [r[0] for r in r2] == [r[0] for r in recs]
    assert (r2[1][2], r2[1][3], r2[1][5]) == (W, H_NEW, CT_NEW), (r2[1][2], r2[1][3], r2[1][5])
    assert r2[2][6] == recs[2][6] + delta and r2[3][6] == recs[3][6] + delta
    assert bytes(new_pak[rec_off:rec_off + 0x18]) == name_bytes, '★ 记录名字被改'
    assert bytes(new_pak[rec_off + 0x1C:rec_off + 0x20]) == w_bytes, '★ w 被改'
    assert bytes(new_pak[rec_off + 0x28:rec_off + 0x438]) == pal_bytes, '★ 调色板被改'
    assert bytes(new_pak[rec_off + 0x20:rec_off + 0x24]) == struct.pack('<I', H_NEW)
    P('[pak] 新 PAK %d B ; 回读 rec: %s' % (len(new_pak), [(r[0], r[2], r[3], hex(r[5])) for r in r2]))
    P('[pak] ★ w 逐字节不变 %s ; 名字不变 ; 调色板 1040 B 不变 ✓' % w_bytes.hex(' '))

    # ── 新 MENU.IMG ──
    old_end = e_pak['off'] + e_pak['stored']
    last_end = max(e['off'] + e['stored'] for e in ents)
    tail_len = last_end - old_end
    P('[menu] PAK end 0x%X ; 最后条目 end %d ; 其后平移区 %d B ; IMG 尾料 %d B'
      % (old_end, last_end, tail_len, hdr['size'] - last_end))
    new_menu = bytearray(iso.read(MENU_LBA * SEC, hdr['size']))
    assert len(new_menu) == hdr['size']
    tail = bytes(new_menu[old_end:last_end])
    new_menu[e_pak['off']:e_pak['off'] + len(new_pak)] = new_pak
    new_menu[old_end + delta:last_end + delta] = tail
    n_off = 0
    for e in ents:
        if e['off'] >= e_ft['off']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             e['off'] + delta)
            n_off += 1
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', new_menu, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
            if a.real_mode == 'fixed':
                struct.pack_into('<I', new_menu,
                                 zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 28,
                                 e['real'] + delta)
    P('[menu] 条目表改动: off %d 条 (+%d) + COMMON.PAK stored 1 条 + real %s'
      % (n_off, delta, ('1 条 (+%d) ★' % delta) if a.real_mode == 'fixed' else '**未改(故意)**'))
    assert n_off == 682, n_off
    assert bytes(new_menu[0:4]) == struct.pack('<I', hdr['size']), '★ IMG 声明长度被改'
    assert bytes(new_menu[hdr['names_start']:hdr['names_end']]) == names0, '★ 名字区被改'
    assert bytes(new_menu[hdr['hash_off']:hdr['hash_off'] + 16384]) == hash0, '★ 哈希表被改'
    # PAK 之前的元数据: 只允许条目表 off/stored
    exp_meta = bytearray(new_menu[0:e_pak['off']])
    for e in ents:
        if e['off'] >= e_ft['off']:
            struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 32,
                             e['off'] + delta)
        if e['idx'] == e_pak['idx']:
            struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 24,
                             e['stored'] + delta)
            if a.real_mode == 'fixed':
                struct.pack_into('<I', exp_meta, zx_lib.TAB_OFF + zx_lib.TAB_STEP * e['idx'] + 28,
                                 e['real'] + delta)
    assert bytes(new_menu[0:e_pak['off']]) == bytes(exp_meta), '★ 元数据出现计划外改动'
    dmeta = sum(1 for i in range(e_pak['off']) if new_menu[i] != iso.mm[MENU_LBA * SEC + i])
    P('[menu] PAK 之前元数据 0x%X B: 计划外改动 0 ; 实际差异 %d 字节 (条目表 %d×4 + stored 4)'
      % (e_pak['off'], dmeta, n_off))

    if a.dry_run:
        P('[dry ] 不写盘')
        _save(a, dict(dry=True, delta=delta, ct_new=CT_NEW, variant=a.variant))
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
    with open(a.dst, 'r+b') as f:
        f.seek(MENU_LBA * SEC)
        f.write(bytes(new_menu))
    P('[out] %s (%d B = %d 扇区)' % (a.dst, os.path.getsize(a.dst), os.path.getsize(a.dst) // SEC))
    assert os.path.getsize(a.dst) == iso.size, '★ ISO 长度被改（本脚本不应加长 ISO）'

    # ── 回读硬断言 ──
    iso2 = tcslib.Iso(a.dst)
    hdr2 = zx_lib.header(iso2, MENU_LBA)
    ents2 = zx_lib.entries(iso2, MENU_LBA)
    e2 = ents2[e_pak['idx']]
    e2ft = ents2[e_ft['idx']]
    pak2 = bytes(iso2.read(e2['iso_off'], e2['stored']))
    r3 = tcslib.parse_pak_records(pak2)
    assert pak2 == new_pak, '★ 回读 PAK 不一致'
    P('[A1] 回读 PAK %d B ; rec#1 psm=0x%02X %dx%d clut=%d px_size=0x%X'
      % (len(pak2), r3[1][1], r3[1][2], r3[1][3], r3[1][4], r3[1][5]))
    assert (r3[1][1], r3[1][2], r3[1][3], r3[1][4], r3[1][5]) == (psm, W, H_NEW, clut, CT_NEW)
    ct2 = pak2[r3[1][6]:r3[1][6] + r3[1][5]]
    assert len(ct2) == CT_NEW
    segs2 = [s for s in tcslib.atlas_container_segments(ct2, W // 2) if s[2] > 0]
    P('[A2] 回读容器 %d B (0x%X) ; %d 段 ; 首行 %s ; 段数据 %s'
      % (len(ct2), len(ct2), len(segs2), [s[0] for s in segs2], [s[2] for s in segs2]))
    assert len(segs2) == 9 and [s[0] for s in segs2] == [64 * k for k in range(8)] + [512]
    assert bytes(pak2[rec_off + 0x1C:rec_off + 0x20]) == w_bytes
    assert bytes(pak2[rec_off + 0x28:rec_off + 0x438]) == pal_bytes
    assert bytes(pak2[rec_off:rec_off + 0x18]) == name_bytes
    P('[A3] ★ w %s 逐字节不变 ; 调色板 1040 B 不变 ; 记录名字不变 ✓' % w_bytes.hex(' '))
    # 旧 8 段 + seg7 数据逐字节等价
    if a.variant == 'minimal':
        assert ct2[0:0x40000] == ct_old[0:0x40000]
        assert segs2[7][2] == 32384
    else:
        assert ct2[0:0x38150] == ct_old[0:0x38150]
        assert segs2[7][2] == 0x8000
    P('[A4] ★ 现役容器前 %d B (0x%X) 逐字节保留 ✓' % (keep, keep))
    assert ct2[CT_NEW - 16:] == ct_old[CT_OLD - 16:]
    P('[A5] 尾部 no-op tag 逐字节相同 %s ✓' % ct2[CT_NEW - 16:].hex(' '))
    ft2 = bytes(iso2.read(e2ft['iso_off'], e2ft['stored']))
    ft1 = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    assert ft2 == ft1 and e2ft['off'] == e_ft['off'] + delta
    P('[A6] FONT.RES %d B 逐字节不变, off 0x%X → 0x%X (+%d) ✓'
      % (len(ft2), e_ft['off'], e2ft['off'], delta))
    t2 = bytes(iso2.read(MENU_LBA * SEC + old_end + delta, tail_len))
    assert t2 == tail
    P('[A7] PAK 之后 %d B 平移区逐字节不变 ✓' % tail_len)
    assert zx_lib.names_region(iso2, MENU_LBA) == names0
    assert zx_lib.hash_region(iso2, MENU_LBA) == hash0
    assert hdr2['size'] == hdr['size']
    P('[A8] 名字区 %d B / 4096 槽哈希表 16,384 B 逐字节不变 ✓ ; IMG 声明 %d 不变 ✓'
      % (len(names0), hdr2['size']))
    ranges = diff_ranges(a.src, a.dst, 1 << 22)
    tot = sum(n for (_, n) in ranges)
    lo = min(o for (o, _) in ranges)
    hi = max(o + n for (o, n) in ranges)
    P('[A9] 逐字节差异区段 %d 个 ; 差异字节合计 %d ; 范围 0x%09X..0x%09X'
      % (len(ranges), tot, lo, hi))
    for (o, n) in ranges[:12]:
        P('       0x%09X .. 0x%09X  (%d B = %.1f KB)' % (o, o + n, n, n / 1024.0))
    if len(ranges) > 12:
        P('       ... 其余 %d 段' % (len(ranges) - 12))
    assert lo >= MENU_LBA * SEC + zx_lib.TAB_OFF, '★ MENU.IMG 元数据之前有改动'
    assert hi <= MENU_LBA * SEC + last_end + delta, '★ 改动越过新最后条目末尾'
    assert lo > MENU_LBA * SEC and hi < MENU_LBA * SEC + hdr['size'], '★ 改动越出 MENU.IMG'
    P('[A10] 改动全在 MENU.IMG 内 (0x%X..0x%X) ✓ ; MENU.IMG 之外逐字节 0 差异 ✓'
      % (MENU_LBA * SEC + zx_lib.TAB_OFF, MENU_LBA * SEC + last_end + delta))
    P('       注: %d 段差异中, 0x%X 之后全部来自"+%d 平移"(已由 [A7] 逐字节证明是纯平移)'
      % (len(ranges), MENU_LBA * SEC + old_end, delta))
    e2r = ents2[e_pak['idx']]
    if a.real_mode == 'fixed':
        assert (e2r['stored'], e2r['real']) == (e_pak['stored'] + delta, e_pak['real'] + delta)
        P('[A11] ★ 回读 COMMON.PAK 条目: stored %d → %d ; **real %d → %d** (+%d, 同步) ✓'
          % (e_pak['stored'], e2r['stored'], e_pak['real'], e2r['real'], delta))
    else:
        assert (e2r['stored'], e2r['real']) == (e_pak['stored'] + delta, e_pak['real'])
        P('[A11] ★ 回读 COMMON.PAK 条目: stored %d → %d ; **real 保持 %d (stored>real, 复现 bug)** ✓'
          % (e_pak['stored'], e2r['stored'], e2r['real']))
    iso2.close()
    iso.close()
    _save(a, dict(dry=False, variant=a.variant, real_mode=a.real_mode, delta=delta,
                  ct_old=CT_OLD, ct_new=CT_NEW,
                  nseg=9, h_old=H_OLD, h_new=H_NEW, w=W,
                  pak_old=len(pak), pak_new=len(new_pak), menu_size=hdr['size'],
                  iso_bytes=os.path.getsize(a.dst), n_off_shift=n_off,
                  h_field_iso=e_pak['iso_off'] + rec_off + 0x20,
                  w_field_iso=e_pak['iso_off'] + rec_off + 0x1C,
                  px_size_field_iso=e_pak['iso_off'] + px_off - 4,
                  container_iso=e_pak['iso_off'] + px_off,
                  seg9_head_iso=e_pak['iso_off'] + px_off + (0x40000 if a.variant == 'minimal'
                                                             else 0x38150 + 48 + 0x8000),
                  diff_ranges=[dict(off=x, len=y) for (x, y) in ranges]))
    return 0


def diff_ranges(p1, p2, blk=1 << 22):
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
    print('[out] %s' % a.report)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
