# -*- coding: utf-8 -*-
r"""fa_ascii_fix.py — ★ 修复 64 列几何吃掉的 ASCII 字形表（只改 FONT.RES 记录 + 跳过带像素）

    python tools/re/toolbelt/fa_ascii_fix.py --src work/builds/GR_FA2400/GR_FA2400.iso \
        --out work/builds/GR_FA2400/GR_FA2400_ascii.iso [--dry-run]

## 问题（A 路 `docs/CAPACITY_2400.md` §3 已实测登记）

图集右边缘 x=992..1023 **正好是新布局的第 62/63 列**：那里原本是三个 face **共享的 ASCII 字形表**
（58 个 8×16 矩形 / 182 条 FT 记录 / 码位 0x21..0x9C：大写字母/数字/标点）。
62 列时引擎永不采样那里；**改成 64 列后必被网格格位覆盖** ⇒ 档案名、名字输入表、ASCII 标点全部乱码
（本轮实拍：`temp/emu_sf/dump/snap_f00019980.png` 的「输入名字」字符表）。

## 本脚本的修法（**不动几何、不丢槽位**）

`tools/re/toolbelt/_dbg_ascii_band.py` 实测：跳过带 y=194..241（**引擎网格永不采样**）里
**y=194..209 共 16 行 × 1024 px 完全空白**；ASCII 表只需 58×8 = 464 px 宽 ⇒ **放得下**。
  ① 把 58 个 ASCII 矩形从 (x≥992, y=0..208) **搬到 y=194..209 的空位**（宽度不变，依次排列）；
  ② 像素从 `GR_F364`（62 列盘，那一带仍完好）**逐 texel 搬过来**；
  ③ 三条 face 的记录 u/v 同步改写（同一矩形共享同一新位置）；
  ④ FONT.RES 槽长 4,421 B **不变**：用 `zx_fontres.py` 的**带来源追踪 LZO1X 原位替换**
     （只改压缩流里的字面量字节，不重新压缩）。

硬断言：
  [A1] 需要搬的记录**全部**在 x≥992 条带里（有例外就停手）
  [A2] 目标空位在 y=194..209 内、逐 texel 与全部记录矩形零交叠、且当前为空
  [A3] 源像素（GR_F364 老坐标）**有墨**
  [A4] FONT.RES 原位替换后：展开态只有目标字节变、长度仍 5,942、槽长仍 4,421
  [A5] 回读：58 条记录指向新位置且像素 == GR_F364 源；其余记录/像素一字未动
  [A6] 图集容器差异 100% 落在新坐标的矩形内；ISO 尺寸不变
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
sys.path.insert(0, os.path.join(REPO, 'tools', 'gr_tools'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                     # noqa: E402
import tcslib as T                                                     # noqa: E402
import zx_lib                                                          # noqa: E402
import fa_build as FB                                                  # noqa: E402
# ★ 注意: **不要** import zx_fontres —— 它是脚本 (模块级会执行分析并写盘)。
#   本脚本自带同一份 lzo_decode_traced/resolve 实现 (逐行对齐 tools/gr_tools/lz77_decode.py)。
from lz77_decode import lzo1x_decompress                                # noqa: E402

OUTDIR = os.path.join(REPO, 'work', 'builds', 'GR_FA2400')
SRC = os.path.join(OUTDIR, 'GR_FA2400.iso')
DST = os.path.join(OUTDIR, 'GR_FA2400_ascii.iso')
PIXSRC = os.path.join(REPO, 'work', 'builds', 'GR_F364', 'GR_F364.iso')
MENU_BASE = zx_lib.MENU_LBA * 2048
BAND = (194, 210)          # y=194..209: 实测全空、且引擎网格不采样的 16 行
LOG = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    LOG.append(s)
    return s


# ── 与 zx_fontres.py 同一实现（逐行照抄 tools/gr_tools/lz77_decode.py，只多记来源）──
def lzo_decode_traced(payload, out_size):
    data = payload
    ip = 0
    n = len(data)
    out = bytearray()
    src = []

    def GETB():
        nonlocal ip
        if ip >= n:
            raise IndexError('input depleted at ip=%d' % ip)
        b = data[ip]
        ip += 1
        return b

    state = 0
    x = GETB()
    if x > 17:
        ln = x - 17
        for k in range(ln):
            out.append(data[ip + k]); src.append(('L', ip + k))
        ip += ln
        x = GETB()
    while True:
        if out_size is not None and len(out) >= out_size:
            break
        if x > 15:
            if x > 63:
                cnt = (x >> 5) - 1
                back = (GETB() << 3) + ((x >> 2) & 7) + 1
            elif x > 31:
                cnt = x & 31
                if cnt == 0:
                    while True:
                        x = GETB()
                        if x:
                            cnt += 31 + x
                            break
                        cnt += 255
                x = GETB()
                back = (GETB() << 6) + (x >> 2) + 1
            else:
                cnt = x & 7
                if cnt == 0:
                    while True:
                        x = GETB()
                        if x:
                            cnt += 7 + x
                            break
                        cnt += 255
                back = (1 << 14) + ((x & 8) << 11)
                x = GETB()
                back += (GETB() << 6) + (x >> 2)
                if back == (1 << 14):
                    break
        elif not state:
            cnt = x & 15
            if cnt == 0:
                while True:
                    x = GETB()
                    if x:
                        cnt += 15 + x
                        break
                    cnt += 255
            ln = cnt + 3
            for k in range(ln):
                out.append(data[ip + k]); src.append(('L', ip + k))
            ip += ln
            x = GETB()
            if x > 15:
                continue
            cnt = 1
            back = (1 << 11) + (GETB() << 2) + (x >> 2) + 1
        else:
            cnt = 0
            back = (GETB() << 2) + (x >> 2) + 1
        o = len(out)
        if back > o:
            return out, src, 'INVALID BACK %d at out=%d' % (back, o)
        for i in range(cnt + 2):
            out.append(out[o - back + i]); src.append(('M', o - back + i))
        state = cnt = x & 3
        for k in range(cnt):
            out.append(data[ip + k]); src.append(('L', ip + k))
        ip += cnt
        if out_size is not None and len(out) >= out_size:
            break
        if ip >= n:
            break
        x = GETB()
    return out, src, None


def resolve(i, src):
    seen = 0
    while True:
        k, v = src[i]
        if k == 'L':
            return v
        i = v
        seen += 1
        assert seen < (1 << 20), '来源链过长'


def rects_of(exp):
    """展开态 → [(face_idx, rec_idx, code, (b0,b1,u0,v0,u1,v1), 记录偏移)]"""
    _he, faces = T.parse_ft_faces(exp)
    p = 28
    out = []
    for fi, (nm, fld, recs) in enumerate(faces):
        l = struct.unpack_from('<I', exp, p)[0]
        p += 4 + l + 56
        nrec = fld[4] * fld[5]
        for r in range(nrec):
            ro = p + 10 * r
            b0, b1, u0, v0, u1, v1 = struct.unpack_from('<BB4H', exp, ro)
            out.append((fi, r, r + 0x20, (b0, b1, u0, v0, u1, v1), ro))
        p += nrec * 10
    return faces, out


def grid_rows(h):
    return [(FB.yrow(r), FB.yrow(r) + 16) for r in range(400) if FB.yrow(r) + 16 <= h]


def window(plane, w, x0, y0, ww, hh):
    return FB.cell_read(plane, x0, y0, w)[:hh, :ww] if (ww == 16 and hh == 16) else None


def read_rect(plane, w, r):
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    g = np.zeros((v1 - v0, u1 - u0), dtype=bool)
    stride = w // 2
    for y in range(v0, v1):
        for x in range(u0, u1):
            b = plane[y * stride + x // 2]
            g[y - v0, x - u0] = (((b >> 4) if (x & 1) else (b & 0x0F)) == 0)
    return g


def write_rect(plane, w, x0, y0, g):
    stride = w // 2
    for i in range(g.shape[0]):
        for j in range(g.shape[1]):
            x, y = x0 + j, y0 + i
            o = y * stride + x // 2
            cur = plane[o]
            v = 0 if g[i, j] else 1
            plane[o] = ((cur & 0x0F) | (v << 4)) if (x & 1) else ((cur & 0xF0) | v)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=SRC)
    ap.add_argument('--out', default=DST)
    ap.add_argument('--pixsrc', default=PIXSRC)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)
    P('=' * 100)
    P('fa_ascii_fix.py — ASCII 字形表搬出 64 列网格（FONT.RES 原位替换 + 跳过带像素搬运）')
    P('  src = %s' % a.src)
    P('  out = %s' % a.out)
    P('  pix = %s (ASCII 像素源, 62 列盘)' % a.pixsrc)
    P('=' * 100)
    F = FB.read_font(a.src)
    w, h = F['w'], F['h']
    iso = F['iso']
    e4 = iso.img_entry(zx_lib.MENU_LBA, 4)
    slot = bytes(iso.read(e4['iso_off'], e4['stored']))
    P('[in  ] FONT.RES #4 stored=%d real=%d' % (e4['stored'], e4['real']))
    exp = b''.join(s[0] for s in T.lzo_subs(slot))
    P('[in  ] 展开态 %d B' % len(exp))
    faces, recs = rects_of(exp)
    P('[in  ] 三个 face: %s ; 记录 %d 条'
      % (', '.join('%s nrec=%d' % (f[0], len(f[2])) for f in faces), len(recs)))

    rows = grid_rows(h)
    def hits_grid(r):
        u0, v0, u1, v1 = r
        if u1 <= u0 or v1 <= v0:
            return False
        return any(v0 < ry1 and ry0 < v1 for (ry0, ry1) in rows)

    bad = [(fi, ri, code, r, ro) for (fi, ri, code, r, ro) in recs
           if hits_grid((r[2], r[3], r[4], r[5]))]
    P('[A1] 落在网格采样行里的记录 = **%d** 条' % len(bad))
    xs = sorted(set((r[2], r[4]) for (_f, _i, _c, r, _o) in bad))
    P('[A1] 涉及 x 区间: %s' % xs)
    assert all(r[2] >= 992 for (_f, _i, _c, r, _o) in bad), '有 x<992 的记录落在网格里 ⇒ 停手'
    P('[A1] 全部在 x≥992 的 ASCII 条带里 ✓')
    # 唯一矩形 (u0,v0,u1,v1) → 需要搬的位置
    uniq = sorted(set((r[2], r[3], r[4], r[5]) for (_f, _i, _c, r, _o) in bad))
    P('[A1] 唯一矩形 %d 个 ; 总宽 %d px' % (len(uniq), sum(u1 - u0 for (u0, _v0, u1, _v1) in uniq)))

    # ── A2 目标空位 ──
    occ = np.zeros((h, w), dtype=bool)
    for (_f, _i, _c, r, _o) in recs:
        u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
        if u1 > u0 and v1 > v0:
            occ[v0:v1, u0:u1] = True
    band_free = ~occ[BAND[0]:BAND[1], :]
    need = sum(u1 - u0 for (u0, _v0, u1, _v1) in uniq) * 16
    # ★ 真正可用的 16 行高空间 = (a) 跳过带里**互不重叠**的空闲 16 行段
    #                            (b) 引擎**不可寻址**的格 (slot ≥ 2350, 永不采样)
    #     （网格采样行的 x 全部被采 ⇒ 网格行里的任何像素都只能放在不可寻址格里）
    used = np.zeros((h, w), dtype=bool)
    cap_band = 0
    for y0 in range(BAND[0], 242 - 15):
        free = ~occ[y0:y0 + 16].any(axis=0)
        cur = None
        for x in range(w + 1):
            v = free[x] if x < w else False
            if v and cur is None:
                cur = x
            elif not v and cur is not None:
                if x - cur >= 8 and not used[y0:y0 + 16, cur:x].any():
                    used[y0:y0 + 16, cur:x] = True
                    cap_band += (x - cur) * 16
                cur = None
    cap_cells = 0
    for s in range(2350, 3000):
        cx, cy = FB.cell(s, 64)
        if cy + 16 > h or cx + 16 > w:
            break
        if not occ[cy:cy + 16, cx:cx + 16].any() and not used[cy:cy + 16, cx:cx + 16].any():
            used[cy:cy + 16, cx:cx + 16] = True
            cap_cells += 256
    cap_ok = cap_band + cap_cells
    P('[A2] 跳过带 y=%d..%d: 空 texel %d / %d ; 整行全空: %s'
      % (BAND[0], BAND[1], int(band_free.sum()), band_free.size,
         [BAND[0] + i for i in range(BAND[1] - BAND[0]) if band_free[i].all()]))
    P('[A2] 需要 16 行高空间 %d px (58 矩形 × 8..16 px 宽 × 16 高)' % need)
    P('[A2] 可用: 跳过带内互不重叠 16 行段 %d px + 不可寻址格(slot≥2350) %d px = **%d px** ⇒ %s'
      % (cap_band, cap_cells, cap_ok,
         '够 ✓' if cap_ok >= need else '★ 不够 (缺 %d px) ⇒ ASCII 表在 h=644/64 列下**搬不了**'
         % (need - cap_ok)))
    if cap_ok < need:
        P('[stop] 硬停手: 无足够连续空位 ⇒ 本修法在现几何下不可行 (见 docs/CAPACITY_2400_FA2400.md §10)')
        return 2
    # 依次排布
    mapping = {}
    x = 0
    for (u0, v0, u1, v1) in uniq:
        wdt, hgt = u1 - u0, v1 - v0
        assert hgt == 16, ('矩形高度不是 16', (u0, v0, u1, v1))
        if x + wdt > w:
            raise SystemExit('跳过带一行放不下: x=%d wdt=%d' % (x, wdt))
        mapping[(u0, v0, u1, v1)] = (x, BAND[0], x + wdt, BAND[0] + hgt)
        x += wdt
    P('[A2] 新位置排布: 用宽 %d px (y=%d..%d) ; 例: %s'
      % (x, BAND[0], BAND[1] - 1, list(mapping.items())[:2]))

    # ── A3 源像素有墨 ──
    S = FB.read_font(a.pixsrc)
    src_pix = {}
    for old, new in mapping.items():
        g = read_rect(S['plane'], S['w'], (0, 0, old[0], old[1], old[2], old[3]))
        src_pix[old] = g
        assert g.any(), ('ASCII 源窗无墨', old)
    P('[A3] %d 个源矩形全部有墨 ✓ (墨量 %d..%d)'
      % (len(src_pix), min(int(g.sum()) for g in src_pix.values()),
         max(int(g.sum()) for g in src_pix.values())))

    # ── A4 FONT.RES 原位替换 ──
    found = None
    for off in range(0, min(len(slot) - 8, 2048)):
        ca, cb = struct.unpack_from('<II', slot, off)
        if not (0 < ca < len(slot) - off - 8) or not (0 < cb <= 1 << 20):
            continue
        try:
            dec, err, _ = lzo1x_decompress(slot[off + 8:off + 8 + ca], out_size=cb)
        except Exception:                                              # noqa: BLE001
            continue
        if err is None and len(dec) == cb and bytes(dec) == exp[:cb]:
            found = (off, ca, cb)
            break
    assert found, '找不到与展开态一致的 LZO 载荷结构'
    pay_off, comp, real = found
    P('[A4] LZO 载荷 @槽+0x%X comp=%d real=%d' % (pay_off, comp, real))
    out, src, err = lzo_decode_traced(slot[pay_off + 8:pay_off + 8 + comp], len(exp))
    assert err is None and bytes(out) == exp, '追踪解码与展开态不一致'
    tgt = bytearray(exp)
    targets = {}
    for (fi, ri, code, r, ro) in bad:
        (u0, v0, u1, v1) = (r[2], r[3], r[4], r[5])
        nu0, nv0, nu1, nv1 = mapping[(u0, v0, u1, v1)]
        for (foff, old_v, new_v) in ((ro + 2, u0, nu0), (ro + 4, v0, nv0),
                                     (ro + 6, u1, nu1), (ro + 8, v1, nv1)):
            ob, nb = struct.pack('<H', old_v), struct.pack('<H', new_v)
            for k in range(2):
                if ob[k] != nb[k]:
                    o = foff + k
                    assert o not in targets or targets[o] == nb[k], ('目标冲突', o)
                    targets[o] = nb[k]
    for o, b in targets.items():
        tgt[o] = b
    P('[A4] 需改展开态字节 %d 个 (矩形 %d 个 × 最多 8 B)' % (len(targets), len(uniq)))
    patch = {}
    lit_users = {}
    for i in range(len(src)):
        k, v = src[i]
        if k == 'L':
            lit_users.setdefault(v, []).append(i)
    conflict = []
    for o, nb in sorted(targets.items()):
        lip = resolve(o, src)
        if lip in patch and patch[lip] != nb:
            conflict.append((o, lip, patch[lip], nb)); continue
        patch[lip] = nb
        for u in lit_users.get(lip, []):
            if u in targets and targets[u] != nb:
                conflict.append(('用户冲突', o, u, nb, targets[u]))
    P('[A4] 需要改的压缩字节 %d 个 ; 冲突 %d %s'
      % (len(patch), len(conflict), '✓' if not conflict else '✗ %s' % conflict[:4]))
    assert not conflict, '压缩流原位替换有冲突 ⇒ 需要走重压缩（本脚本不做）'
    pay = bytearray(slot[pay_off + 8:pay_off + 8 + comp])
    for ip, nb in patch.items():
        pay[ip] = nb
    slot2 = bytearray(slot)
    slot2[pay_off + 8:pay_off + 8 + comp] = pay
    exp2 = b''.join(s[0] for s in T.lzo_subs(bytes(slot2)))
    assert len(exp2) == len(exp), (len(exp2), len(exp))
    nchg = sum(1 for i in range(len(exp)) if exp2[i] != exp[i])
    assert exp2 == bytes(tgt), '回读展开态 != 目标'
    P('[A4] 原位替换后: 槽长 %d (不变) ✓ ; 展开态 %d B (不变) ✓ ; 变化字节 %d == 目标 %d ✓'
      % (len(slot2), len(exp2), nchg, len(targets)))
    assert len(slot2) == len(slot) == e4['stored']

    # ── 像素搬运 ──
    plane = bytearray(F['plane'])
    for old, new in mapping.items():
        write_rect(plane, w, new[0], new[1], src_pix[old])
    # 断言: 新位置像素 == 源 ; 老位置未被本脚本碰 (它现在放着网格字形, 保持原样)
    for old, new in mapping.items():
        got = read_rect(bytes(plane), w, (0, 0, new[0], new[1], new[2], new[3]))
        assert (got == src_pix[old]).all(), ('搬运后不一致', old)
    P('[A5] %d 个矩形搬到 y=%d..%d 后逐 texel == GR_F364 源 ✓'
      % (len(mapping), BAND[0], BAND[1] - 1))

    if a.dry_run:
        P('[dry ] 全部断言通过, 未写盘')
        return 0
    # ── 写盘 ──
    with open(a.out, 'wb') as fo, open(a.src, 'rb') as fi:
        for blk in iter(lambda: fi.read(1 << 22), b''):
            fo.write(blk)
    ct_new, _segs, _cov = FB.plane_to_container(F['ct'], bytes(plane), w)
    px_off = MENU_BASE + F['e_pak']['off'] + F['PX']
    with open(a.out, 'r+b') as f:
        f.write  # noqa: B018
        f.seek(e4['iso_off']); f.write(bytes(slot2))
        f.seek(px_off); f.write(ct_new)
    P('[out ] %s (%d B)' % (a.out, os.path.getsize(a.out)))

    # ── A5/A6 回读 ──
    G = FB.read_font(a.out)
    e4b = G['iso'].img_entry(zx_lib.MENU_LBA, 4)
    slotb = bytes(G['iso'].read(e4b['iso_off'], e4b['stored']))
    assert slotb == bytes(slot2), 'FONT.RES 回读不一致'
    expb = b''.join(s[0] for s in T.lzo_subs(slotb))
    assert expb == bytes(tgt), '展开态回读不一致'
    faces2, recs2 = rects_of(expb)
    n_ok = 0
    for (fi, ri, code, r, ro) in bad:
        got = struct.unpack_from('<BB4H', expb, ro)
        want = (r[0], r[1]) + mapping[(r[2], r[3], r[4], r[5])]
        assert got == want, (code, got, want)
        n_ok += 1
    P('[A5] 回读: %d 条记录已指向新位置 ✓' % n_ok)
    same_other = sum(1 for i in range(len(exp)) if i not in targets and exp[i] != expb[i])
    assert same_other == 0
    P('[A5] 展开态除目标字节外 0 处不同 ✓')
    for old, new in mapping.items():
        got = read_rect(G['plane'], G['w'], (0, 0, new[0], new[1], new[2], new[3]))
        assert (got == src_pix[old]).all()
    P('[A5] 回读像素 == GR_F364 源 ✓ ; 网格格位未动 (槽 0..2349 逐格哈希另验)')
    # 容器差异窗口
    d = [i for i in range(len(F['ct'])) if F['ct'][i] != ct_new[i]]
    P('[A6] 图集容器差异字节 %d ; 范围 0x%X..0x%X (应只在跳过带 y=%d..%d)'
      % (len(d), min(d), max(d), BAND[0], BAND[1] - 1))
    assert os.path.getsize(a.out) == os.path.getsize(a.src)
    P('[A6] ISO 尺寸不变 ✓ (%d B)' % os.path.getsize(a.out))
    hh = hashlib.sha256()
    with open(a.out, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 22), b''):
            hh.update(blk)
    rep = dict(src=a.src, out=a.out, n_records=len(bad), n_rects=len(uniq),
               band=list(BAND), pack_width=x, targets=len(targets), patch_bytes=len(patch),
               ct_diff=len(d), out_sha256=hh.hexdigest())
    with io.open(os.path.join(OUTDIR, 'temp', 'fa_ascii_fix_report.json'), 'w',
                 encoding='utf-8', newline='\n') as f:
        json.dump(dict(extra=rep, log=LOG), f, ensure_ascii=False, indent=1)
    P('[out] %s' % os.path.join(OUTDIR, 'temp', 'fa_ascii_fix_report.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
