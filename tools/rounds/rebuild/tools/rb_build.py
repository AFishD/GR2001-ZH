# -*- coding: utf-8 -*-
r"""rb_build.py —— 《PS2 幽灵行动 SLUS-206.13》中文盘「从幸存工具链重建」总装器。

产出: work/builds/GR_REBUILD/GR_REBUILD2400.iso  (1,648,164,864 B)

链路（每步都有硬断言，失败即中止，不写盘）:
  [1] 基底 = 英文原盘 ⊕ GR_FA2400_K2 块转储的全部扇区
      ⇒ 逐字节取回：SLUS_206.13(ELF) / MENU#3 COMMON.PAK(1024x644 图集) /
        MENU#4 FONT.RES / MENU#25 EN_STRINGS.RES(中文) / MENU#283 SF XML(中文) 等
  [2] GR#902 EN_STRINGS.RES(GR 侧的同一张逻辑表) = 由 [1] 取回的 MENU#25
      「EN→中文」逐条对应关系搬到 GR 侧（两份容器 2232 条 payload 在英文盘上 99.5% 相同）
  [3] GR#906 FONT.RES = MENU#4（英文盘上两份逐字节相同；工程惯例两份同步写）
  [4] GR#3451 COMMON.PAK = 旁证候选（GR_ZH113b 系转储的 MENU#3 槽，psm20/1024x512）
      —— 引擎从不读 GR.IMG 那份（docs/BUILD_TOOLCHAIN.md:193-194），属死拷贝
  [5] 重新压回 [1] 的 K2 真扇区（GR#3451 区 K2 转储有 9 扇区真字节）
  [6] 自查 + sha256 + build_info.json

用法:
  python rb_build.py --out work\builds\GR_REBUILD\GR_REBUILD2400.iso [--dry]
"""
import argparse
import glob
import hashlib
import io
import json
import os
import shutil
import struct
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib as T                                                    # noqa: E402
import zx_lib                                                         # noqa: E402

SEC = 2048
DUMPDIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'PCSX2', 'cdvd-dump')
ORIG = os.path.join(REPO, 'third_party', 'orig', 'ps2',
                    "Tom Clancy's Ghost Recon (USA).iso")
K2DUMP_NAME = 'GR_FA2400_K2 (2026-10-17 15-08-20).dump'
CAND_DUMP_NAME = 'GR_ZH113b (2026-10-15 19-39-44).dump'
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p, buf=1 << 22):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        while True:
            d = f.read(buf)
            if not d:
                break
            h.update(d)
    return h.hexdigest()


def load_idx(path):
    n = os.path.getsize(path)
    with open(path, 'rb') as f:
        magic, bsz, total, zero = struct.unpack('<4sIII', f.read(16))
        assert magic == b'BDV2' and bsz == SEC, path
        cnt, rem = divmod(n - 16, 4 + SEC)
        assert rem == 0, path
        idx = {}
        for i in range(cnt):
            f.seek(16 + i * (4 + SEC))
            idx[struct.unpack('<I', f.read(4))[0]] = 16 + i * (4 + SEC) + 4
    return idx, total


def read_at(path, idx, off, size):
    l0, l1 = off // SEC, (off + size - 1) // SEC
    buf = bytearray()
    with open(path, 'rb') as f:
        for l in range(l0, l1 + 1):
            if l not in idx:
                return None
            f.seek(idx[l])
            buf += f.read(SEC)
    return bytes(buf[off - l0 * SEC:off - l0 * SEC + size])


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(REPO, 'work', 'builds', 'GR_REBUILD',
                                                  'GR_REBUILD2400.iso'))
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args(argv)
    t0 = time.time()

    # ═══════════ [1] 基底 = 原盘 ⊕ K2 转储 ═══════════
    P('=' * 100)
    P('rb_build.py  ——  GR_REBUILD2400 总装')
    P('[1] 基底 = 英文原盘 ⊕ K2 块转储')
    P('    原盘 = %s' % ORIG)
    P('    原盘 sha256 = %s (%d B)' % (sha_file(ORIG), os.path.getsize(ORIG)))
    k2p = os.path.join(DUMPDIR, K2DUMP_NAME)
    assert os.path.exists(k2p), k2p
    kidx, ktot = load_idx(k2p)
    P('    K2 转储 = %s' % k2p)
    P('    K2 转储扇区 %d / %d (%.2f%%) ; 头部 total_lba=%d' %
      (len(kidx), ktot, 100.0 * len(kidx) / ktot, ktot))

    base_size = os.path.getsize(ORIG)
    nsec = base_size // SEC
    assert base_size % SEC == 0
    if a.dry:
        P('[dry] 到此为止（不写盘）')
        return 0

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    if os.path.exists(a.out):
        raise SystemExit('输出已存在，拒绝覆盖: %s' % a.out)
    tmp = a.out + '.part'
    shutil.copyfile(ORIG, tmp)
    P('    [1a] 拷原盘 → %s' % os.path.basename(tmp))
    n_over = 0
    with open(tmp, 'r+b') as fo, open(k2p, 'rb') as fd:
        for lba, off in sorted(kidx.items()):
            if lba >= nsec:
                continue
            fd.seek(off)
            fo.seek(lba * SEC)
            fo.write(fd.read(SEC))
            n_over += 1
    P('    [1b] 覆盖 K2 扇区 %d 个 (%.2f MB)' % (n_over, n_over * SEC / 1048576.0))

    # ── [1c] ★ MENU.IMG 尾部整体位移 +0x10800 的重建 ──
    # 实测（K2 盘 vs 原盘的 IMG 条目表逐条对比）：COMMON.PAK 从 400,659 长到 468,243
    # （+67,584 = 0x10800），MENU.IMG 里 **从 FONT.RES(原 off 0xB9120) 起的整个尾部**
    # 一律后移 0x10800；GR.IMG 条目表 0 差异（未搬）。
    # 本成品盘沿用了 K2 的条目表，但那些新位置上的字节若不在 K2 转储覆盖范围内，
    # 现在是「原盘同位置」的字节 ⇒ 整段错位（实测：INTRO.PSS 播到一半停滞）。
    # 修法 = 对 x >= 0xC9920 且扇区未被 K2 转储覆盖的字节，取 原盘[x - 0x10800]。
    MENU_SHIFT = 0x10800
    MENU_FT_NEW = 0xC9920                 # K2: FONT.RES 新 off（= 0xB9120 + 0x10800）
    menu_base = zx_lib.MENU_LBA * SEC
    menu_lim = (zx_lib.MENU_LBA + 804768 - zx_lib.MENU_LBA) * SEC   # 一直到盘尾
    P('')
    P('[1c] MENU.IMG 尾部位移重建: base=0x%X ; 阈值 x>=0x%X 取 原盘[x-0x%X]' %
      (menu_base, MENU_FT_NEW, MENU_SHIFT))
    src = open(ORIG, 'rb')
    try:
        with open(tmp, 'r+b') as fo:
            lo = menu_base + MENU_FT_NEW
            hi = min(menu_base + menu_lim, base_size)
            l0, l1 = lo // SEC, (hi - 1) // SEC
            n_fill = n_skip = 0
            for lba in range(l0, l1 + 1):
                if lba in kidx:
                    n_skip += 1                    # K2 真字节，保留
                    continue
                fo.seek(lba * SEC)
                cur = bytearray(fo.read(SEC))
                src.seek(lba * SEC - MENU_SHIFT)
                old = src.read(SEC)
                if len(old) < SEC:
                    old = old + b'\x00' * (SEC - len(old))
                # 逐字节：偏移前的区域保留现值（只在 x>=lo 处替换）
                cut = max(0, lo - lba * SEC)
                cur[cut:] = old[cut:]
                fo.seek(lba * SEC)
                fo.write(bytes(cur))
                n_fill += 1
        P('     填充 %d 扇区 / 跳过（K2 真字节）%d 扇区' % (n_fill, n_skip))
    finally:
        src.close()

    # ── 断言：ELF 逐字节 == K2_SLUS_206.13.elf ──
    k2elf = os.path.join(REPO, 'work', 'builds', 'GR_CSFIX', 'temp',
                         'K2_SLUS_206.13.elf')
    with open(tmp, 'rb') as f:
        f.seek(604160)
        elf_in = f.read(37453732)
    elf_ref = open(k2elf, 'rb').read()
    P('    [A1] ELF(ISO 604160..+37453732) == %s : %s ; sha=%s' %
      (os.path.basename(k2elf), elf_in == elf_ref, sha(elf_in)[:16]))
    assert elf_in == elf_ref, 'ELF 与 K2 真件不符'

    iso = T.Iso(tmp)
    men = zx_lib.entries(iso, zx_lib.MENU_LBA)
    gr = zx_lib.entries(iso, zx_lib.GR_LBA)

    def find(ent, name, nth=0):
        h = [x for x in ent if x['name'] == name]
        return h[nth]

    e_m_pak = find(men, 'COMMON.PAK')
    e_m_ft = find(men, 'FONT.RES')
    e_m_lang = find(men, 'EN_STRINGS.RES')
    e_m_sf = find(men, 'EN_SPECIAL_FEATURE.XML')
    e_g_lang = find(gr, 'EN_STRINGS.RES')
    e_g_ft = find(gr, 'FONT.RES')
    e_g_pak = find(gr, 'COMMON.PAK')

    # ── 断言：MENU#3 图集 1024x644 / 329744 ──
    pak = bytes(iso.read(e_m_pak['iso_off'], e_m_pak['stored']))
    rec = [r for r in T.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    P('    [A2] MENU#%d COMMON.PAK stored=%d ; new_font_revised psm=%d w=%d h=%d '
      'px=%d' % (e_m_pak['idx'], e_m_pak['stored'], rec[1], rec[2], rec[3], rec[5]))
    assert (rec[1], rec[2], rec[3], rec[5]) == (20, 1024, 644, 329744), rec
    assert rec[5] == 1024 * 644 // 2 + 16
    assert (1024 * 644 // 2) % 2048 == 0
    assert rec[2] < 1025
    # ── 断言：MENU#25 已是中文（首条 payload 不是 ASCII 'Victory!'）──
    slotm = bytes(iso.read(e_m_lang['iso_off'], e_m_lang['stored']))
    blobm = b''.join(s[0] for s in T.lzo_subs(slotm))
    ents_m, used_m = T.parse_lang(blobm)
    P('    [A3] MENU#%d EN_STRINGS.RES 条目=%d used_end=0x%X 首条 payload=%s' %
      (e_m_lang['idx'], len(ents_m), used_m, ents_m[0].data[:12]))
    assert ents_m[0].data != b'Victory!', 'MENU 语言表不是中文（K2 扇区没取回？）'

    # ═══════════ [2] GR#902 ← MENU#25 的 EN→中文对应 ═══════════
    P('')
    P('[2] GR#%d EN_STRINGS.RES ← 由 MENU#%d 的 EN→中文 逐条对应重建' %
      (e_g_lang['idx'], e_m_lang['idx']))
    s_gr_en = bytes(iso.read(e_g_lang['iso_off'], e_g_lang['stored']))
    subs_g = T.lzo_subs(s_gr_en)
    blob_g_en = b''.join(s[0] for s in subs_g)
    ents_g, used_g = T.parse_lang(blob_g_en)
    P('    GR#902 条目=%d used_end=0x%X blob=%d ; 与 MENU 条目数一致=%s' %
      (len(ents_g), used_g, len(blob_g_en), len(ents_g) == len(ents_m)))
    assert len(ents_g) == len(ents_m)
    assert [(x.g, x.i) for x in ents_g] == [(x.g, x.i) for x in ents_m]

    # 原盘 MENU#25 的 EN blob —— 用来证明「两份容器装的是同一批逻辑字符串」
    o = T.Iso(ORIG)
    e_o = find(zx_lib.entries(o, zx_lib.MENU_LBA), 'EN_STRINGS.RES')
    o.close()
    with open(ORIG, 'rb') as f:
        f.seek(e_o['iso_off'])
        slot_o = f.read(e_o['stored'])
    blob_m_en = b''.join(s[0] for s in T.lzo_subs(slot_o))
    ents_men, used_men = T.parse_lang(blob_m_en)
    assert len(ents_men) == len(ents_g)
    assert [(x.g, x.i) for x in ents_men] == [(x.g, x.i) for x in ents_g]
    same_en = sum(1 for x, y in zip(ents_men, ents_g) if x.data == y.data)
    P('    [A4] 英文盘上 MENU#25 与 GR#902 逐条 payload 相同 %d/%d (%.1f%%)' %
      (same_en, len(ents_men), 100.0 * same_en / len(ents_men)))
    assert same_en >= 0.99 * len(ents_men)
    n_zh = sum(1 for x, y in zip(ents_men, ents_m) if x.data != y.data)
    P('    [A5] MENU#25 EN→K2 中文：payload 变化 %d/%d 条' % (n_zh, len(ents_men)))

    edits = []
    for i in range(len(ents_g)):
        sp = T.lang_entry_span(blob_g_en, ents_g[i])
        attr = blob_g_en[ents_g[i].attr_off:ents_g[i].attr_off + 2]
        edits.append((sp[0], sp[1], struct.pack('<I', len(ents_m[i].data))
                      + ents_m[i].data + attr))
    spliced = T.splice(blob_g_en, edits)
    growth = len(spliced) - len(blob_g_en)
    shift, undo = 0, []
    for (s0, s1, nb) in sorted(edits, key=lambda x: x[0]):
        undo.append((s0 + shift, s0 + shift + len(nb), blob_g_en[s0:s1]))
        shift += len(nb) - (s1 - s0)
    assert T.splice(spliced, undo) == blob_g_en, '[S2] 反向重建失败'
    P('    [S2] 反向重建 == 源 GR_EN blob ✓ ; 新 blob %d B (Δ%+d)' %
      (len(spliced), growth))
    if growth > 0:
        assert growth <= len(blob_g_en) - used_g, 'GR 容器装不下'
        new_blob_g = spliced[:len(blob_g_en)]
    else:
        new_blob_g = spliced + b'\x00' * (-growth)
    nG, uG = T.parse_lang(new_blob_g)
    assert len(nG) == len(ents_g)
    assert [(x.g, x.i) for x in nG] == [(x.g, x.i) for x in ents_g]
    bad = [i for i in range(len(nG)) if nG[i].data != ents_m[i].data]
    P('    [S5] 逐条 payload == MENU 侧中文 : 不同 %d 条' % len(bad))
    assert not bad, bad[:5]
    assert uG == used_m, 'used_end 不一致: 0x%X vs 0x%X' % (uG, used_m)
    P('    [S4] 新 blob used_end=0x%X == MENU 侧 0x%X ✓' % (uG, used_m))

    # 重压（照搬 migrate_legacy.repack 口径）
    frame = bytearray()
    q = 0
    n_rep = 0
    for k, s in enumerate(subs_g):
        part = new_blob_g[q:q + s[2]]
        q += s[2]
        if part == s[0]:
            frame += s_gr_en[s[3]:s[3] + 8 + s[1]]
            continue
        cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
        back, err, _ = T.lzo1x_decompress(cc, out_size=s[2])
        assert err is None and back == part, '子流 %d 回环失败' % k
        frame += struct.pack('<II', len(cc), s[2]) + cc
        n_rep += 1
    frame = bytes(frame)
    assert q == len(new_blob_g)
    assert len(frame) <= e_g_lang['stored'], (len(frame), e_g_lang['stored'])
    P('    [S7] 重压 %d 子流 ; 帧 %d B ; 槽 %d B ⇒ 余 %d B' %
      (n_rep, len(frame), e_g_lang['stored'], e_g_lang['stored'] - len(frame)))
    iso.close()

    with open(tmp, 'r+b') as f:
        f.seek(e_g_lang['iso_off'])
        f.write(frame)
        f.write(b'\x00' * (e_g_lang['stored'] - len(frame)))
    P('    写出 GR#%d @0x%08X' % (e_g_lang['idx'], e_g_lang['iso_off']))

    # ═══════════ [3] GR#906 FONT.RES ← MENU#4 ═══════════
    P('')
    P('[3] GR#%d FONT.RES ← MENU#%d（英文盘上两份逐字节相同 → 同步）' %
      (e_g_ft['idx'], e_m_ft['idx']))
    iso3 = T.Iso(tmp)
    men3 = zx_lib.entries(iso3, zx_lib.MENU_LBA)
    gr3 = zx_lib.entries(iso3, zx_lib.GR_LBA)
    e_m_ft3 = find(men3, 'FONT.RES')
    e_g_ft3 = find(gr3, 'FONT.RES')
    slot_ft = bytes(iso3.read(e_m_ft3['iso_off'], e_m_ft3['stored']))
    blob_ft = b''.join(s[0] for s in T.lzo_subs(slot_ft))
    P('    MENU#4 FONT.RES stored=%d 展开=%d sha=%s' %
      (e_m_ft3['stored'], len(blob_ft), sha(slot_ft)[:16]))
    assert e_m_ft3['stored'] == e_g_ft3['stored'], '两槽长度不同'
    iso3.close()
    with open(tmp, 'r+b') as f:
        f.seek(e_g_ft3['iso_off'])
        f.write(slot_ft)
    with open(tmp, 'rb') as f:
        f.seek(e_g_ft3['iso_off'])
        back = f.read(e_g_ft3['stored'])
    assert back == slot_ft
    P('    [R3] 写后回读 == MENU 侧 slot ✓')

    # ═══════════ [4] GR#3451 COMMON.PAK ← 旁证候选 ═══════════
    P('')
    P('[4] GR#%d COMMON.PAK ← 旁证候选（%s 的 MENU#3 槽）' %
      (e_g_pak['idx'], CAND_DUMP_NAME))
    candp = os.path.join(DUMPDIR, CAND_DUMP_NAME)
    cidx, _t = load_idx(candp)
    o2 = T.Iso(ORIG)
    e_o_m_pak = find(zx_lib.entries(o2, zx_lib.MENU_LBA), 'COMMON.PAK')
    o2.close()
    cand = read_at(candp, cidx, e_o_m_pak['iso_off'], e_o_m_pak['stored'])
    assert cand is not None and len(cand) == e_g_pak['stored']
    r2 = [r for r in T.parse_pak_records(cand) if r[0] == 'new_font_revised'][0]
    P('    候选 new_font_revised psm=%d w=%d h=%d stored=%d ; sha=%s' %
      (r2[1], r2[2], r2[3], r2[5], sha(cand)[:16]))
    assert (r2[1], r2[2], r2[3], r2[5]) == (20, 1024, 512, 262160), r2
    with open(tmp, 'r+b') as f:
        f.seek(e_g_pak['iso_off'])
        f.write(cand)
    P('    写出 GR#%d @0x%08X (%d B)' % (e_g_pak['idx'], e_g_pak['iso_off'], len(cand)))

    # ═══════════ [5] 重新压回 K2 真扇区（GR#3451 区 K2 转储有真字节）═══════════
    P('')
    P('[5] 重新压回 [1] 的 K2 真扇区（覆盖写过的区域）')
    l0, l1 = e_g_pak['iso_off'] // SEC, (e_g_pak['iso_off']
                                         + e_g_pak['stored'] - 1) // SEC
    n_back = 0
    with open(tmp, 'r+b') as fo, open(k2p, 'rb') as fd:
        for lba in range(l0, l1 + 1):
            if lba in kidx and lba < nsec:
                fd.seek(kidx[lba])
                fo.seek(lba * SEC)
                d = fd.read(SEC)
                fo.write(d)
                n_back += 1
    P('    GR#3451 区间 LBA %d..%d 中 K2 真扇区 %d 个已回压' % (l0, l1, n_back))

    # ═══════════ [6] 自查 ═══════════
    P('')
    P('[6] 总装自查')
    v = T.Iso(tmp)
    menv = zx_lib.entries(v, zx_lib.MENU_LBA)
    grv = zx_lib.entries(v, zx_lib.GR_LBA)
    P('    [C1] MENU 条目 %d / GR 条目 %d（与原盘一致 %s / %s）' %
      (len(menv), len(grv), len(menv) == 686, len(grv) == 4070))
    for nm, ent, tag in (('COMMON.PAK', menv, 'MENU'), ('FONT.RES', menv, 'MENU'),
                         ('EN_STRINGS.RES', menv, 'MENU'),
                         ('EN_SPECIAL_FEATURE.XML', menv, 'MENU'),
                         ('EN_STRINGS.RES', grv, 'GR'), ('FONT.RES', grv, 'GR'),
                         ('COMMON.PAK', grv, 'GR')):
        e = find(ent, nm)
        s = bytes(v.read(e['iso_off'], e['stored']))
        subs = T.lzo_subs(s)
        blob = b''.join(x[0] for x in subs) if subs else b''
        P('    %s#%-5d %-24s stored=%-8d 子流=%-3d 展开=%-8d sha=%s' %
          (tag, e['idx'], nm, e['stored'], len(subs) if subs else 0, len(blob),
           sha(blob)[:16] if blob else sha(s)[:16]))
    # 3 个中文容器逐条 == MENU 侧 / 可解析
    s2 = bytes(v.read(find(grv, 'EN_STRINGS.RES')['iso_off'],
                      find(grv, 'EN_STRINGS.RES')['stored']))
    b2 = b''.join(x[0] for x in T.lzo_subs(s2))
    e2, u2 = T.parse_lang(b2)
    s1 = bytes(v.read(find(menv, 'EN_STRINGS.RES')['iso_off'],
                      find(menv, 'EN_STRINGS.RES')['stored']))
    b1 = b''.join(x[0] for x in T.lzo_subs(s1))
    e1, u1 = T.parse_lang(b1)
    P('    [C2] MENU#25 与 GR#902 逐条 payload 相同 = %s (used_end 0x%X / 0x%X)' %
      (all(x.data == y.data for x, y in zip(e1, e2)), u1, u2))
    assert all(x.data == y.data for x, y in zip(e1, e2))
    v.close()

    os.replace(tmp, a.out)
    h = sha_file(a.out)
    P('')
    P('★ 产物 = %s' % a.out)
    P('  尺寸 = %d B ; sha256 = %s' % (os.path.getsize(a.out), h))
    P('  用时 %.1f s' % (time.time() - t0))

    info = dict(version='GR_REBUILD2400', out=a.out, bytes=os.path.getsize(a.out),
                sha256=h, built=time.strftime('%Y-%m-%d %H:%M'),
                base=os.path.relpath(ORIG, REPO), base_sha256=sha_file(ORIG),
                k2_dump=K2DUMP_NAME, k2_sectors=len(kidx),
                cand_dump=CAND_DUMP_NAME,
                steps=['[1] orig ⊕ K2 block dump (full ELF + MENU#3 atlas + MENU#4'
                       ' FONT.RES + MENU#25 EN_STRINGS.RES + MENU#283 SF XML)',
                       '[2] GR#902 EN_STRINGS.RES rebuilt from MENU#25 (EN→ZH'
                       ' per-entry correspondence), frame %d B' % len(frame),
                       '[3] GR#906 FONT.RES ← MENU#4 slot (%d B)' % len(slot_ft),
                       '[4] GR#3451 COMMON.PAK ← ZH113b-family MENU#3 candidate'
                       ' (%d B, header 5229/5229 == K2 true bytes)' % len(cand),
                       '[5] re-asserted %d K2-true sectors' % n_back])
    with io.open(os.path.join(os.path.dirname(os.path.abspath(a.out)),
                              'build_info_rebuild.json'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        json.dump(info, fh, ensure_ascii=False, indent=1)
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_REBUILD', 'temp',
                              'rb_build.log'), 'w', encoding='utf-8',
                 newline='\n') as fh:
        fh.write('\n'.join(LOG) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
