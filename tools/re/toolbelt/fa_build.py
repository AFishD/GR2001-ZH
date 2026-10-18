# -*- coding: utf-8 -*-
r"""fa_build.py — GR_FA2400 成品盘：5 个借槽字形 + 恢复 1736..1871 + 保留空模板

    python tools/re/toolbelt/fa_build.py --dry-run          # 只跑断言, 不写盘
    python tools/re/toolbelt/fa_build.py                    # 写 work/builds/GR_FA2400/GR_FA2400.iso

配方（复用 cap_build.py 的容器读写 + zx_lib.ft_records, 不重造轮子）:
  base  = work/builds/GR_MERGE2400/GR_MERGE2400.iso   (h=644 / 64 列 / GATE 0xBA / 文本已迁移)
  写入 4 段:
    ① 借槽 2345..2348 ← 按/时/小/击 的 **large face FT 记录 idx 153/152/151/150** 采样窗 (16x16)
    ② 借槽 2349     ← ✕ 图标字形 (见 report 的「来源判定」: 盘上无源 ⇒ 用 r84 对 △ 的同一配方
                       render16(方正像素16.ttf,'×'); pda_counterparts 是 20x20 彩色精灵, 不能逐 texel 落格)
    ③ 槽 1736..1871 ← **恢复** r84 的 136 个真字形 (取自 GR_F364/F365, 62 列格 → 64 列格)
                       ★ 为什么必须恢复: 现役 charset 的 pair_of 把 136 个字映射到 slot 1736..1871,
                         而 GR_CAP2400/GR_MERGE2400 把这一段写成了探针图案 ⇒ 不恢复 = 136 个字缺字形
    ④ 槽 1872..2344 ← 确定性空模板 (16 行全 0x11 = 全透明), 清掉探针图案

硬断言 (任一失败即中止, 不写盘):
  [1] 源窗有墨 (空窗 = 找错记录)          [2] 三个 face 的表对照 (224/224/96) 逐条登记
  [3] 写入后回读槽逐 texel == 源窗        [4] 0..1735 与基底逐 texel 不变
  [5] 1736..1871 回读 == GR_F364/F365     [6] 1872..2344 回读全空
  [7] ELF 5 字节 = 0xBA/64 状态不变      [8] 3 个文本容器逐字节不变
  [9] 全盘差异 100% 落在容器窗口内 ; ISO 尺寸不变
"""
import argparse
import hashlib
import io
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                     # noqa: E402
import tcslib as T                                                     # noqa: E402
import zx_lib                                                          # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_FA2400')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_MERGE2400', 'GR_MERGE2400.iso')
RESTORE_SRC = os.path.join(REPO, 'work', 'builds', 'GR_F364', 'GR_F364.iso')
RESTORE_CHK = os.path.join(REPO, 'work', 'builds', 'GR_F365', 'GR_F365.iso')
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
VA2ISO = lambda va: va - 0x6C780
COLS_VA = 0x4170AC
ELF_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
MENU_BASE = zx_lib.MENU_LBA * 2048
W, NCOL = 1024, 64
EMPTY_NIB = 1
GATE = 0xBA
TEXT_CONTAINERS = ('EN_STRINGS.RES', 'EN_SPECIAL_FEATURE.XML')
# 借槽 (borrowed_pairs.json): pair (lead,trail) → slot = (lead-0xA1)*94 + (trail-0xA1)
BORROW = [('按', 0xB9, 0xFA, 2345, 'FT large idx153 (code 0xB9)'),
          ('时', 0xB9, 0xFB, 2346, 'FT large idx152 (code 0xB8)'),
          ('小', 0xB9, 0xFC, 2347, 'FT large idx151 (code 0xB7)'),
          ('击', 0xB9, 0xFD, 2348, 'FT large idx150 (code 0xB6)'),
          ('\u2715', 0xB9, 0xFE, 2349, 'render16(方正像素16.ttf, U+00D7) [见来源判定]')]
KEEP_LO, KEEP_HI = 1736, 1871          # 恢复段
EMPTY_LO, EMPTY_HI = 1872, 2344        # 保留空段
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def yrow(row):
    return 2 + 16 * (row + (3 if row >= 12 else 0))


def cell(slot, ncol=NCOL):
    return 16 * (slot % ncol), yrow(slot // ncol)


def slot_of_pair(b1, b2):
    return (b1 - 0xA1) * 94 + (b2 - 0xA1)


def cell_read(plane, x, y, w=W):
    stride = w // 2
    g = np.zeros((16, 16), dtype=bool)
    for i in range(16):
        r = plane[(y + i) * stride + x // 2:(y + i) * stride + x // 2 + 8]
        g[i, 0::2] = [(b & 0x0F) == 0 for b in r]
        g[i, 1::2] = [(b >> 4) == 0 for b in r]
    return g


def cell_write(plane, x, y, g, w=W):
    stride = w // 2
    for i in range(16):
        row = bytearray(8)
        for k in range(8):
            lo = EMPTY_NIB if not g[i, 2 * k] else 0
            hi = EMPTY_NIB if not g[i, 2 * k + 1] else 0
            row[k] = (hi << 4) | lo
        plane[(y + i) * stride + x // 2:(y + i) * stride + x // 2 + 8] = row


def render16(ch):
    """r84 zx_r84_tri.py 的同一实现 (FZXS16 16px → 16x16 布尔墨窗)。"""
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    out = a[8:24, 8:24] < 128
    full = a < 128
    fys, fxs = np.where(full)
    assert len(fys) and fys.min() >= 8 and fxs.min() >= 8 and fys.max() < 24 and fxs.max() < 24, \
        '墨越出 16x16 em 窗: %r' % ch
    return out


def container_to_plane(cont, w, h):
    stride = w // 2
    segs = [s for s in T.atlas_container_segments(bytes(cont), stride) if s[2] > 0]
    plane = bytearray(b'\x11' * (stride * h))
    for (row0, doff, nb) in segs:
        nfull, rest = nb // stride, nb % stride
        for i in range(nfull):
            if row0 + i < h:
                plane[(row0 + i) * stride:(row0 + i + 1) * stride] = \
                    cont[doff + i * stride:doff + (i + 1) * stride]
        if rest and row0 + nfull < h:
            d = (row0 + nfull) * stride
            plane[d:d + rest] = cont[doff + nfull * stride:doff + nfull * stride + rest]
    return bytes(plane)


def plane_to_container(stage_cont, plane, w):
    stride = w // 2
    out = bytearray(stage_cont)
    segs = [s for s in T.atlas_container_segments(bytes(stage_cont), stride) if s[2] > 0]
    covered = 0
    for (row0, doff, nb) in segs:
        nfull, rest = nb // stride, nb % stride
        for i in range(nfull):
            out[doff + i * stride:doff + (i + 1) * stride] = \
                plane[(row0 + i) * stride:(row0 + i + 1) * stride]
        if rest:
            d = (row0 + nfull) * stride
            out[doff + nfull * stride:doff + nfull * stride + rest] = plane[d:d + rest]
        covered += nb
    return bytes(out), segs, covered


def read_font(iso_path):
    iso = T.Iso(iso_path)
    ents = zx_lib.entries(iso, zx_lib.MENU_LBA)
    e_pak = [e for e in ents if e['name'] == 'COMMON.PAK'][0]
    e_ft = [e for e in ents if e['name'] == 'FONT.RES'][0]
    pak = bytes(iso.read(e_pak['iso_off'], e_pak['stored']))
    recs = T.parse_pak_records(pak)
    nm, psm, w, h, clut, px_size, PX = recs[1]
    ct = pak[PX:PX + px_size]
    ft_slot = bytes(iso.read(e_ft['iso_off'], e_ft['stored']))
    ft_blob = b''.join(s[0] for s in T.lzo_subs(ft_slot))
    faces, ft_end = zx_lib.ft_records(ft_blob, 28)
    return dict(iso=iso, path=iso_path, e_pak=e_pak, e_ft=e_ft, pak=pak, recs=recs,
                name=nm, psm=psm, w=w, h=h, clut=clut, px_size=px_size, PX=PX, ct=ct,
                plane=container_to_plane(ct, w, h), faces=faces, ft_slot=ft_slot,
                ft_blob=ft_blob, ft_end=ft_end)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--restore-src', default=RESTORE_SRC)
    ap.add_argument('--restore-chk', default=RESTORE_CHK)
    ap.add_argument('--out', default=os.path.join(OUTDIR, 'GR_FA2400.iso'))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    os.makedirs(os.path.join(OUTDIR, 'temp'), exist_ok=True)
    P('=' * 100)
    P('fa_build.py  GR_FA2400 成品盘')
    P('  base        = %s' % a.base)
    P('  restore-src = %s   (+独立互证 %s)' % (a.restore_src, a.restore_chk))
    P('  out         = %s' % a.out)
    P('=' * 100)

    B = read_font(a.base)
    w, h, px_size = B['w'], B['h'], B['px_size']
    assert (B['name'], B['psm'], w, h) == ('new_font_revised', 0x14, W, 644), (B['name'], B['psm'], w, h)
    # ── 三闸门 (图集几何) ──
    P('[gate1] w=%d ≤ 1024 ✓ ; h=%d ; 行数 %d ⇒ %d 列 × %d 行 = %d 格 ≥ 2350 ✓'
      % (w, h, sum(1 for r in range(200) if yrow(r) + 16 <= h), NCOL,
         sum(1 for r in range(200) if yrow(r) + 16 <= h),
         NCOL * sum(1 for r in range(200) if yrow(r) + 16 <= h)))
    P('[gate2] px_size = 0x%X = %d ; w*h/2+16 = %d %s'
      % (px_size, px_size, w * h // 2 + 16, '✓' if px_size == w * h // 2 + 16 else '✗'))
    assert px_size == w * h // 2 + 16
    P('[gate3] (w*h/2) %% 2048 = %d %s' % ((w * h // 2) % 2048,
                                           '✓' if (w * h // 2) % 2048 == 0 else '✗'))
    assert (w * h // 2) % 2048 == 0
    P('[ct   ] 容器 %d B ; 段数 %d ; payload %d'
      % (len(B['ct']), len([s for s in T.atlas_container_segments(B['ct'], w // 2) if s[2] > 0]),
         sum(s[2] for s in T.atlas_container_segments(B['ct'], w // 2) if s[2] > 0)))

    # ── ELF 5 字节现状核对 (本轮不再改 ELF) ──
    mm = B['iso'].mm
    elf = []
    v = struct.unpack_from('<I', mm, VA2ISO(COLS_VA))[0]
    elf.append(dict(va='0x%08X' % COLS_VA, iso='0x%08X' % VA2ISO(COLS_VA), word='%08X' % v,
                    imm=v & 0xFFFF, want=NCOL, tag='COLS'))
    for va in ELF_SITES:
        vv = struct.unpack_from('<I', mm, VA2ISO(va))[0]
        elf.append(dict(va='0x%08X' % va, iso='0x%08X' % VA2ISO(va), word='%08X' % vv,
                        imm=vv & 0xFFFF, want=GATE, tag='GATE'))
    for e in elf:
        P('[elf ] %-9s VA %s ISO %s  %s  imm=0x%02X (期望 0x%02X) %s'
          % (e['tag'], e['va'], e['iso'], e['word'], e['imm'], e['want'],
             '✓' if e['imm'] == e['want'] else '✗'))
        assert e['imm'] == e['want'], e
    P('[elf ] 共 5 个站点: 1 列数 + 4 闸门, 每个只改小端 imm 低字节 = **5 字节** (已由 A 路设好, 本轮不动)')

    # ── ① 源窗: large face FT idx 150..153 + 三 face 对照 ──
    faces = {nm: (fld, rows) for (nm, fld, rows) in B['faces']}
    P('')
    P('[face] 三个 face: %s' % ', '.join('%s nrec=%d' % (nm, len(faces[nm][1]))
                                         for nm in ('large', 'default', 'huge')))
    face_cmp = {}
    for code in (0xB6, 0xB7, 0xB8, 0xB9, 0xB5, 0xB1):
        idx = code - 0x20
        row = {}
        for nm in ('large', 'default', 'huge'):
            fld, rows = faces[nm]
            if idx >= len(rows):
                row[nm] = dict(oom=True, nrec=len(rows))
                continue
            _o, r = rows[idx]
            row[nm] = dict(oom=False, rect=list(r[2:6]), b0=r[0], b1=r[1],
                           ink=int(cell_read(B['plane'], r[2], r[3], w).sum())
                           if (r[4] - r[2] == 16 and r[5] - r[3] == 16) else None)
        face_cmp['0x%02X' % code] = row
        same = (not row['large']['oom'] and not row['default']['oom']
                and row['large']['rect'] == row['default']['rect'])
        P('[face] 0x%02X idx=%-3d large=%s default=%s huge=%s ⇒ large/default %s ; huge %s'
          % (code, idx, row['large'].get('rect'), row['default'].get('rect'),
             row['huge'].get('rect'), '同格 ✓' if same else '★不同 ✗',
             '越界 (nrec=%d < idx) ⇒ 该 face 无此字' % row['huge']['nrec']
             if row['huge'].get('oom') else '有记录'))
        if not row['huge'].get('oom'):
            assert row['huge']['rect'] == row['large']['rect'], ('huge 与 large 不同格', code)
    # large vs default 全表逐条比较 (不只这几个字)
    lr = faces['large'][1]
    dr = faces['default'][1]
    ndiff = sum(1 for i in range(min(len(lr), len(dr))) if lr[i][1] != dr[i][1])
    P('[face] large vs default **全表** %d 条记录逐条比较: 不同 %d 条 %s'
      % (min(len(lr), len(dr)), ndiff, '✓' if ndiff == 0 else '✗'))
    assert ndiff == 0, 'large/default 记录表不同 ⇒ 停手'
    ndiff_h = sum(1 for i in range(min(len(lr), len(faces['huge'][1])))
                  if lr[i][1] != faces['huge'][1][i][1])
    P('[face] large vs huge 前 %d 条: 不同 %d 条 (huge nrec=%d = 另一套字号表, 与 CJK 槽无关)'
      % (min(len(lr), len(faces['huge'][1])), ndiff_h, len(faces['huge'][1])))

    # ── ✕ 图标来源判定 (盘上取证) ──
    P('')
    P('[icon] ✕ (0xB5) 来源判定:')
    for code in (0xB1, 0xB5):
        fld, rows = faces['large']
        _o, r = rows[code - 0x20]
        P('[icon]   0x%02X (FT idx %d): rect=(%d,%d)-(%d,%d) %dx%d ; 窗内墨 = %d %s'
          % (code, code - 0x20, r[2], r[3], r[4], r[5], r[4] - r[2], r[5] - r[3],
             int(cell_read(B['plane'], r[2], r[3], w)[:, :r[4] - r[2]].sum())
             if r[4] - r[2] <= 16 else -1,
             '← 空占位记录 (与 docs/PLACEHOLDER_AND_SYMBOLS.md §1 一致)' if code == 0xB5 else ''))
    icon_src = dict(
        determined_by='tools/text_csv/icon_table.py §二 ICON_CODES[0xB5] + tcslib PUA 口径',
        engine_source='纹理 pda_counterparts.rsb (COMMON.PAK rec#3 256x256 PSM8) UV (1,198)-(21,218)',
        font_atlas_source=None,
        why_not='该精灵是 20x20 彩色键帽 (深色圆 + 蓝叉), 且是**另一张贴图**; '
                '图集格是 16x16 单色 (nibble 0=墨/1=透明) ⇒ 无法逐 texel 落格',
        hunt='fa_cross_hunt.py: 2088 个候选窗 (544 记录 + 槽) XOR 比对 + 全平面扫描 (距离≤12) '
             '⇒ 盘上**不存在**任何叉形字形 (最好距离 19)',
        fallback='r84 对 △(槽 1504) 的同一配方: render16(third_party/fonts/方正像素16.ttf, \'×\')')
    for k, v in icon_src.items():
        P('[icon]   %-18s = %s' % (k, v))

    # ── ② 目标像素面 ──
    plane_new = bytearray(B['plane'])
    touch = {}          # slot -> dict(src, window, ink)
    # (a) 恢复 1736..1871
    S = read_font(a.restore_src)
    C = read_font(a.restore_chk)
    assert (S['w'], S['h']) == (1024, 640), (S['w'], S['h'])
    P('')
    P('[rest] 恢复源 %s : %dx%d ; %s 互证' % (os.path.basename(a.restore_src), S['w'], S['h'],
                                            os.path.basename(a.restore_chk)))
    nbad = 0
    for s in range(KEEP_LO, KEEP_HI + 1):
        gs = cell_read(S['plane'], *cell(s, 62))
        gc = cell_read(C['plane'], *cell(s, 62))
        if not (gs == gc).all():
            nbad += 1
        assert gs.any(), '恢复源槽 %d 无墨' % s
        cell_write(plane_new, *cell(s, NCOL), gs)
        touch[s] = dict(src='restore:%s slot%d (62列格)' % (os.path.basename(a.restore_src), s),
                        ink=int(gs.sum()), window=None)
    P('[rest] 槽 %d..%d 共 %d 格: 源窗全部有墨 ✓ ; 两源逐 texel 不同 %d %s'
      % (KEEP_LO, KEEP_HI, KEEP_HI - KEEP_LO + 1, nbad, '✓' if nbad == 0 else '✗'))
    assert nbad == 0
    # (b) 清成保留空模板
    empty = np.zeros((16, 16), dtype=bool)
    for s in range(EMPTY_LO, EMPTY_HI + 1):
        cell_write(plane_new, *cell(s, NCOL), empty)
        touch[s] = dict(src='empty-template (16 行 x 0x11)', ink=0, window=None)
    P('[empt] 槽 %d..%d 共 %d 格 → 确定性空模板 (全透明 0x11)'
      % (EMPTY_LO, EMPTY_HI, EMPTY_HI - EMPTY_LO + 1))
    # (c) 5 个借槽
    P('')
    for (nm, b1, b2, slot, src) in BORROW:
        assert slot_of_pair(b1, b2) == slot, (nm, slot, slot_of_pair(b1, b2))
        if nm == '\u2715':
            g = render16('\u00d7')
            srcwin = None
            assert g.any(), '✕ 模板为空'
        else:
            code = {2345: 0xB9, 2346: 0xB8, 2347: 0xB7, 2348: 0xB6}[slot]
            idx = code - 0x20
            _o, r = faces['large'][1][idx]
            assert r[4] - r[2] == 16 and r[5] - r[3] == 16, ('源记录不是 16x16', nm, r)
            srcwin = b''.join(bytes(B['plane'][(r[3] + i) * (w // 2) + r[2] // 2:
                                               (r[3] + i) * (w // 2) + r[2] // 2 + 8])
                              for i in range(16))
            g = cell_read(B['plane'], r[2], r[3], w)
        ink = int(g.sum())
        P('[slot] %s pair=0x%02X%02X → 槽 %d ← %s ; 源窗墨 = %d %s'
          % (nm, b1, b2, slot, src, ink, '✓ 有墨' if ink > 0 else '✗ 空窗'))
        assert ink > 0, '源窗无墨 (空窗 = 找错记录) ⇒ 立即停手: %s' % nm
        cell_write(plane_new, *cell(slot, NCOL), g)
        touch[slot] = dict(src=src, ink=ink, pair='%02X%02X' % (b1, b2),
                           src_win_sha=hashlib.sha256(srcwin).hexdigest() if srcwin else None,
                           window=np.asarray(g, dtype=bool).astype(int).tolist())

    # ── ③ 回读断言 (在内存像素面上先验一遍) ──
    P('')
    for (nm, b1, b2, slot, src) in BORROW:
        got = cell_read(bytes(plane_new), *cell(slot, NCOL))
        exp = np.array(touch[slot]['window'], dtype=bool)
        assert (got == exp).all(), '槽 %d 回读 != 源窗' % slot
        P('[A1] 槽 %d (%s) 回读逐 texel == 源窗: ✓ (墨 %d)' % (slot, nm, int(got.sum())))
    nchg = 0
    for s in range(0, 1736):
        if (cell_read(bytes(B['plane']), *cell(s, NCOL)) != cell_read(bytes(plane_new), *cell(s, NCOL))).any():
            nchg += 1
    P('[A2] 槽 0..1735 (现役 + r83) 逐 texel 与基底相同: %s (不同 %d)'
      % ('✓' if nchg == 0 else '✗', nchg))
    assert nchg == 0
    for s in range(KEEP_LO, KEEP_HI + 1):
        assert (cell_read(bytes(plane_new), *cell(s, NCOL))
                == cell_read(S['plane'], *cell(s, 62))).all(), s
    P('[A3] 槽 %d..%d 回读 == %s 源格: ✓ (%d 格)'
      % (KEEP_LO, KEEP_HI, os.path.basename(a.restore_src), KEEP_HI - KEEP_LO + 1))
    for s in range(EMPTY_LO, EMPTY_HI + 1):
        assert not cell_read(bytes(plane_new), *cell(s, NCOL)).any(), s
    P('[A4] 槽 %d..%d 回读全空 (保留槽): ✓ (%d 格)'
      % (EMPTY_LO, EMPTY_HI, EMPTY_HI - EMPTY_LO + 1))
    # 格格互不重叠
    seen = {}
    for s in range(0, 2350):
        cx, cy = cell(s, NCOL)
        assert 0 <= cx and cx + 16 <= w and 0 <= cy and cy + 16 <= h, (s, cx, cy)
        assert (cx, cy) not in seen, ('格位重复', s, seen[(cx, cy)])
        seen[(cx, cy)] = s
    P('[A5] 槽 0..2349 (2350 格) 全部映到图集内**互不重复**的 16x16 格 ✓')

    # ── ④ 容器回写 ──
    ct_new, segs, covered = plane_to_container(B['ct'], bytes(plane_new), w)
    assert len(ct_new) == len(B['ct']) and covered == sum(s[2] for s in
                                                          T.atlas_container_segments(B['ct'], w // 2) if s[2] > 0)
    plane_rt = container_to_plane(ct_new, w, h)
    assert plane_rt == bytes(plane_new), '容器回环不一致'
    P('[ct  ] 新容器 %d B (同长) ; 容器→引擎面 回环逐字节相同 ✓' % len(ct_new))
    # 容器差异字节必须落在被改的格里
    touched_cells = set()
    for s in touch:
        touched_cells.add(cell(s, NCOL))
    diff_bytes = []
    for i in range(len(B['ct'])):
        if B['ct'][i] != ct_new[i]:
            diff_bytes.append(i)
    P('[ct  ] 容器差异字节 %d 个 ; 差异范围 0x%X..0x%X'
      % (len(diff_bytes), min(diff_bytes), max(diff_bytes)))
    # 逐字节反查 (字节偏移 → 引擎面 (x,y)) 是否落在被改格
    segs_list = [s for s in T.atlas_container_segments(B['ct'], w // 2) if s[2] > 0]
    bad_out = 0
    for o in diff_bytes:
        yy = xx = None
        for (row0, doff, nb) in segs_list:
            if doff <= o < doff + nb:
                d = o - doff
                yy = row0 + d // (w // 2)
                xx = (d % (w // 2)) * 2
                break
        if yy is None:
            bad_out += 1
            continue
        hit = any(cx <= xx and xx + 1 < cx + 16 and cy <= yy < cy + 16
                  for (cx, cy) in touched_cells)
        if not hit:
            bad_out += 1
    P('[ct  ] 差异字节**全部落在被改的 16x16 格内**: %s (格外的 %d 个)'
      % ('✓' if bad_out == 0 else '✗', bad_out))
    assert bad_out == 0

    pak_new = bytearray(B['pak'])
    pak_new[B['PX']:B['PX'] + px_size] = ct_new
    pak_new = bytes(pak_new)
    assert len(pak_new) == len(B['pak'])
    r2 = T.parse_pak_records(pak_new)
    assert (r2[1][2], r2[1][3], r2[1][5]) == (w, h, px_size)
    P('[pak ] 新 PAK %d B (同长) ; rec#1 %dx%d px_size=0x%X ✓ ; 容器外字节不变 ✓'
      % (len(pak_new), r2[1][2], r2[1][3], r2[1][5]))

    # ── ⑤ 文本容器/ELF/尺寸 不变 (与基底逐字节) ──
    keep = {}
    for nm in TEXT_CONTAINERS:
        hits = [e for e in zx_lib.entries(B['iso'], zx_lib.GR_LBA) if e['name'] == nm]
        for e in hits:
            keep['GR:%s@%d' % (nm, e['idx'])] = (e['iso_off'], e['stored'])
    for nm in TEXT_CONTAINERS:
        hits = [e for e in zx_lib.entries(B['iso'], zx_lib.MENU_LBA) if e['name'] == nm]
        for e in hits:
            keep['MENU:%s@%d' % (nm, e['idx'])] = (e['iso_off'], e['stored'])
    P('[keep] 待核对「不许变」的容器 %d 个: %s' % (len(keep), ', '.join(sorted(keep))))

    rep = dict(base=a.base, out=a.out, restore_src=a.restore_src, restore_chk=a.restore_chk,
               w=w, h=h, ncol=NCOL, px_size=px_size, gate=GATE, elf=elf, face_cmp=face_cmp,
               icon_src=icon_src, borrow=[dict(char=nm, pair='%02X%02X' % (b1, b2), slot=s,
                                               src=src, ink=touch[s]['ink'])
                                       for (nm, b1, b2, s, src) in BORROW],
               keep=dict(lo=KEEP_LO, hi=KEEP_HI, src=a.restore_src),
               empty=dict(lo=EMPTY_LO, hi=EMPTY_HI),
               ct_diff_bytes=len(diff_bytes),
               ct_diff_range=['0x%X' % min(diff_bytes), '0x%X' % max(diff_bytes)],
               base_sha=sha256_file(a.base), base_size=os.path.getsize(a.base))
    if a.dry_run:
        P('')
        P('[dry ] --dry-run: 全部断言通过, 未写盘')
        _save(rep, dry=True)
        B['iso'].close()
        return 0

    # ── ⑥ 写盘 ──
    with open(a.base, 'rb') as fi, open(a.out, 'wb') as fo:
        for blk in iter(lambda: fi.read(1 << 22), b''):
            fo.write(blk)
    with open(a.out, 'r+b') as f:
        f.seek(MENU_BASE + B['e_pak']['off'] + B['PX'])
        f.write(ct_new)
    P('')
    P('[out ] %s  %d B  sha256=%s' % (a.out, os.path.getsize(a.out), sha256_file(a.out)))

    # ── ⑦ 回读产物盘 ──
    Z = read_font(a.out)
    assert Z['ct'] == ct_new and Z['px_size'] == px_size
    assert (Z['w'], Z['h']) == (w, h)
    P('[R1 ] 回读容器逐字节 == 写前 ✓ ; %dx%d px_size=0x%X ✓' % (Z['w'], Z['h'], Z['px_size']))
    for (nm, b1, b2, slot, src) in BORROW:
        got = cell_read(Z['plane'], *cell(slot, NCOL))
        exp = np.array(touch[slot]['window'], dtype=bool)
        assert (got == exp).all()
        P('[R2 ] 回读槽 %d (%s) 逐 texel == 源窗 ✓ (墨 %d)' % (slot, nm, int(got.sum())))
    ok_keep = sum(1 for s in range(KEEP_LO, KEEP_HI + 1)
                  if (cell_read(Z['plane'], *cell(s, NCOL)) == cell_read(S['plane'], *cell(s, 62))).all())
    assert ok_keep == KEEP_HI - KEEP_LO + 1
    P('[R3 ] 回读槽 %d..%d == %s: %d/%d ✓'
      % (KEEP_LO, KEEP_HI, os.path.basename(a.restore_src), ok_keep, KEEP_HI - KEEP_LO + 1))
    ok_empty = sum(1 for s in range(EMPTY_LO, EMPTY_HI + 1)
                   if not cell_read(Z['plane'], *cell(s, NCOL)).any())
    assert ok_empty == EMPTY_HI - EMPTY_LO + 1
    P('[R4 ] 回读槽 %d..%d 全空: %d/%d ✓' % (EMPTY_LO, EMPTY_HI, ok_empty, EMPTY_HI - EMPTY_LO + 1))
    ok_live = sum(1 for s in range(0, KEEP_LO)
                  if (cell_read(Z['plane'], *cell(s, NCOL)) == cell_read(B['plane'], *cell(s, NCOL))).all())
    assert ok_live == KEEP_LO
    P('[R5 ] 回读槽 0..%d == 基底逐 texel: %d/%d ✓' % (KEEP_LO - 1, ok_live, KEEP_LO))
    assert Z['ft_slot'] == B['ft_slot'], 'FONT.RES 变了'
    P('[R6 ] FONT.RES %d B 逐字节不变 ✓' % len(Z['ft_slot']))
    zmm = Z['iso'].mm
    for e in elf:
        vv = struct.unpack_from('<I', zmm, int(e['iso'], 16))[0]
        assert (vv & 0xFFFF) == e['want'], e
    P('[R7 ] ELF 5 站点 imm 全部 = 期望值 (COLS=%d, GATE=0x%02X) ✓' % (NCOL, GATE))

    # ── ⑧ 全盘差异窗口 ──
    if os.path.getsize(a.out) != os.path.getsize(a.base):
        P('[D  ] ★ ISO 尺寸变化: %d → %d' % (os.path.getsize(a.base), os.path.getsize(a.out)))
    allow = [(MENU_BASE + B['e_pak']['off'] + B['PX'],
              MENU_BASE + B['e_pak']['off'] + B['PX'] + px_size)]
    n_in = n_out = 0
    ex = []
    szb = os.path.getsize(a.base)
    with open(a.out, 'rb') as fo, open(a.base, 'rb') as fb:
        pos = 0
        while pos < szb:
            n = min(1 << 22, szb - pos)
            bo, bb = fo.read(n), fb.read(n)
            if bo != bb:
                for i in range(n):
                    if bo[i] != bb[i]:
                        p = pos + i
                        if any(lo <= p < hi for (lo, hi) in allow):
                            n_in += 1
                        else:
                            n_out += 1
                            if len(ex) < 8:
                                ex.append((p, bb[i], bo[i]))
            pos += n
    P('[D  ] 全盘差异 vs 基底(GR_MERGE2400): 计划窗口内 %d B ; **窗口外 %d B** %s'
      % (n_in, n_out, '✓' if n_out == 0 else '✗ %s' % ex))
    P('[D  ] 窗口 = 图集容器 [0x%X, 0x%X) (%d B)'
      % (allow[0][0], allow[0][1], px_size))
    assert n_out == 0, ex
    # 3 个文本容器逐字节不变
    for k, (off, ln) in sorted(keep.items()):
        same = Z['iso'].read(off, ln) == B['iso'].read(off, ln)
        P('[D  ] %-32s @0x%08X %7d B 逐字节不变: %s' % (k, off, ln, '✓' if same else '✗'))
        assert same, k
    rep.update(out_sha=sha256_file(a.out), out_size=os.path.getsize(a.out),
               ct_diff_outside=0, diff_in_window=n_in, diff_out_window=n_out)
    rep['slots'] = dict(borrow=[b['slot'] for b in rep['borrow']],
                        restored=[KEEP_LO, KEEP_HI], empty=[EMPTY_LO, EMPTY_HI],
                        n_addressable=2350)
    rep['windows'] = {s: dict(src=touch[s]['src'], ink=touch[s]['ink'],
                              src_win_sha=touch[s].get('src_win_sha'))
                      for s in touch}
    # 逐槽窗口位图 (取证)
    with io.open(os.path.join(OUTDIR, 'temp', 'glyph_windows.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump({str(row[3]): touch[row[3]]['window'] for row in BORROW}, f, indent=1)
    _save(rep, dry=False)
    B['iso'].close()
    Z['iso'].close()
    S['iso'].close()
    C['iso'].close()
    return 0


def _save(rep, dry):
    name = 'fa_build_dry_report.json' if dry else 'fa_build_report.json'
    with io.open(os.path.join(OUTDIR, 'temp', name), 'w', encoding='utf-8', newline='\n') as f:
        json.dump(dict(extra=rep, log=LOG), f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUTDIR, 'temp', 'fa_build%s.log' % ('_dry' if dry else '')),
                 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    P('[out] %s' % os.path.join(OUTDIR, 'temp', name))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
