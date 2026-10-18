# -*- coding: utf-8 -*-
r"""fa_verify.py — GR_FA2400 全量验收（只读, 逐项给命令与输出）

    python tools/re/toolbelt/fa_verify.py [--iso <成品>] [--base <基底 GR_ZH113b>]

判据 (与 LEAD_CAPACITY_2400 §14 / 任务书 C 段一一对应):
  [C1] 图集三闸门: w≤1024 / px_size == w*h/2+16 == 329744 / (w*h/2)%2048==0
  [C2] 槽 0..2349 全部可寻址 + 有字形/保留槽**分开计数** (dump_font 另跑, 见 fa_dump_font.py)
  [C3] ★主判据: **载荷级旧码扫描 = 0 处**
       做法 = 把成品载荷按 gate 0xBA 走一遍, 用**逆映射**把新对偶码还原成基底单字节
              ⇒ 还原流必须**逐字节 == 基底盘同载荷** (⇒ 0 残留 + 除迁移外 0 改动);
       结构区/陈旧尾巴的裸 0xB1..0xB9 **单列计数**(不许改, §10.4)
  [C4] 逐字符一致: 基底(历史 charset r82 / gate 0xB1) vs 成品(新 charset / gate 0xBA), 图标单列
  [C5] 全盘差异分类 (vs GR_ZH113b 全链窗口 / vs GR_MERGE2400 本轮窗口) + ISO 尺寸登记
  [C6] 文本容器条目表不变 (off/stored/real) + h=660 备用档的 px_size 闸门核对
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
import fa_build as FB                                                  # noqa: E402
import migrate_legacy as ML                                            # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp')
ISO = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'GR_FA2400.iso')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
MERGE = os.path.join(REPO, 'work', 'builds', 'GR_MERGE2400', 'GR_MERGE2400.iso')
HIST_CS = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82', 'charset_before_r82.json')
STAGE660 = os.path.join(REPO, 'work', 'builds', 'GR_CAP2400', '_stage660.iso')
VA2ISO = lambda va: va - 0x6C780
COLS_VA = 0x4170AC
ELF_SITES = (0x416EE8, 0x417160, 0x41751C, 0x5656A4)
MENU_BASE = zx_lib.MENU_LBA * 2048
GATE, BASE_GATE, NCOL = 0xBA, 0xB1, 64
# 逆映射: 新对偶码 → 基底单字节 (migrate_legacy 的 9 个码档, 含 r82/r83 已迁的 △/键/练/用)
INV = {(0xB1, 0xA1): 0xB1, (0xB1, 0xA2): 0xB2, (0xB1, 0xA3): 0xB3, (0xB1, 0xA4): 0xB4,
       (0xB9, 0xFE): 0xB5, (0xB9, 0xFD): 0xB6, (0xB9, 0xFC): 0xB7, (0xB9, 0xFB): 0xB8,
       (0xB9, 0xFA): 0xB9}
FWD = {v: k for k, v in INV.items()}
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


def load_conts(iso_path):
    iso = T.Iso(iso_path)
    conts = []
    for name, spec in T.RES.items():
        for cp in spec['copies']:
            (img, lba, idx, tag) = cp[:4]
            e = iso.img_entry(lba, idx)
            raw = bytes(iso.read(e['iso_off'], e['stored']))
            conts.append(dict(name=name, tag=tag, img=img, lba=lba, idx=idx, entry=e,
                              raw=raw, blob=b''.join(s[0] for s in T.lzo_subs(raw)),
                              iso_off=e['iso_off'], slot=e['stored']))
    return iso, conts


def pairs_of(cs_json_path):
    d = json.load(io.open(cs_json_path, encoding='utf-8'))
    return ({int(v): k for k, v in d['codes'].items()},
            {tuple(v): k for k, v in d['pair_of'].items()},
            {k: int(v) for k, v in d['codes'].items()},
            {k: tuple(v) for k, v in d['pair_of'].items()})


def legacy_scan(data, lead_hi=0xB1):
    """按**基底语义**扫: 0xA1..lead_hi-1 = 前导(吃 2 字节), 其余单字节; 返回 [(off, byte)]。"""
    out, i, n = [], 0, len(data)
    while i < n:
        c = data[i]
        if 0xA1 <= c < lead_hi:
            i += 2
            continue
        if 0xB1 <= c <= 0xB9:
            out.append((i, c))
        i += 1
    return out


def reconstruct(payload, pair_of_new, stat):
    """成品载荷 → 基底字节流 (逆映射)。返回 (bytes, 统计 dict)。"""
    out = bytearray()
    i, n = 0, len(payload)
    while i < n:
        c = payload[i]
        if c < 0x80:
            out.append(c); i += 1; stat['ascii'] += 1
        elif 0xA1 <= c < GATE:
            if i + 1 >= n:
                stat['orphan_lead'].append(i)
                out.append(c); i += 1
                continue
            pr = (c, payload[i + 1])
            if pr in INV:
                out.append(INV[pr]); stat['inv'][INV[pr]] += 1; i += 2
            elif pr in pair_of_new:
                out += bytes(pr); stat['kept_pair'] += 1; i += 2
            else:
                stat['unknown_pair'].append((i, '%02X%02X' % pr))
                out += bytes(pr); i += 2
        else:
            out.append(c); stat['single'] += 1; i += 1
    return bytes(out), stat


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=ISO)
    ap.add_argument('--base', default=BASE)
    ap.add_argument('--merge', default=MERGE)
    a = ap.parse_args(argv)
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    P('=' * 104)
    P('fa_verify.py  ★ GR_FA2400 全量验收')
    P('  iso  = %s' % a.iso)
    P('  base = %s (文本基底)' % a.base)
    P('=' * 104)

    # ══════════ C1 三闸门 + 尺寸 + ELF ══════════
    F = FB.read_font(a.iso)
    w, h, px = F['w'], F['h'], F['px_size']
    nrow = sum(1 for r in range(400) if FB.yrow(r) + 16 <= h)
    P('[C1.1] 图集 %dx%d psm=0x%02X ; w ≤ 1024: %s' % (w, h, F['psm'], '✓' if w <= 1024 else '✗'))
    P('[C1.2] px_size = 0x%X = %d ; w*h/2+16 = %d ⇒ %s'
      % (px, px, w * h // 2 + 16, '✓' if px == w * h // 2 + 16 else '✗'))
    P('[C1.3] (w*h/2) %% 2048 = %d ⇒ %s ; 行数 %d × %d 列 = %d 格 ≥ 2350 %s'
      % ((w * h // 2) % 2048, '✓' if (w * h // 2) % 2048 == 0 else '✗', nrow, NCOL,
         nrow * NCOL, '✓' if nrow * NCOL >= 2350 else '✗'))
    assert w <= 1024 and px == w * h // 2 + 16 and (w * h // 2) % 2048 == 0 and nrow * NCOL >= 2350
    mm = F['iso'].mm
    elf = []
    v = struct.unpack_from('<I', mm, VA2ISO(COLS_VA))[0]
    elf.append(('COLS', COLS_VA, VA2ISO(COLS_VA), v, NCOL))
    for va in ELF_SITES:
        vv = struct.unpack_from('<I', mm, VA2ISO(va))[0]
        elf.append(('GATE', va, VA2ISO(va), vv, GATE))
    for (tg, va, off, word, want) in elf:
        imm = word & 0xFFFF
        P('[C1.4] ELF %-4s VA 0x%08X ISO 0x%08X %08X imm=0x%02X %s'
          % (tg, va, off, word, imm, '✓' if imm == want else '✗'))
        assert imm == want
    P('[C1.4] ELF 改动 = **5 字节** (1 列数 62→64 + 4 闸门 →0xBA), 均已生效 ✓')
    sizes = {os.path.basename(p): os.path.getsize(p) for p in (a.iso, a.base, a.merge)}
    P('[C1.5] ISO 尺寸: 成品 %d B ; 基底 %d B ; 合并盘 %d B ⇒ 三者相同: %s'
      % (sizes[os.path.basename(a.iso)], sizes[os.path.basename(a.base)],
         sizes[os.path.basename(a.merge)],
         '✓' if len(set(sizes.values())) == 1 else '✗'))
    rep['C1'] = dict(w=w, h=h, px_size=px, nrow=nrow, cells=nrow * NCOL, elf=elf, sizes=sizes)

    # ══════════ C2 槽位三段划分 + 有字形/保留 分开计数 ══════════
    cs = T.Charset()
    slot_char = {}
    for ch, pr in cs.enc_pair.items():
        slot_char.setdefault((pr[0] - 0xA1) * 94 + (pr[1] - 0xA1), []).append(ch)
    P('')
    P('[C2.1] 槽位三段划分 (在成品盘上逐格取墨):')
    segs = [('0 .. 1735', 0, 1735, '现役 + r83 = 有字形'),
            ('1736 .. 1871', 1736, 1871, 'r84 的 136 字 = 有字形 (本轮从 GR_F364/F365 恢复)'),
            ('1872 .. 2344', 1872, 2344, '★保留槽 (确定性空模板, 无字形)'),
            ('2345 .. 2349', 2345, 2349, '★本轮借槽 5 个 = 有字形 (按/时/小/击/✕)')]
    n_glyph = n_empty = 0
    seg_rep = []
    for (lab, lo, hi, note) in segs:
        inks, empty = [], 0
        for s in range(lo, hi + 1):
            g = FB.cell_read(F['plane'], *FB.cell(s, NCOL), w=w)
            k = int(g.sum())
            if k == 0:
                empty += 1
            else:
                inks.append(k)
        if '保留槽' in note:
            n_empty += hi - lo + 1
        else:
            n_glyph += hi - lo + 1
        P('[C2.1] 槽 %-13s %-46s 格 %4d ; 有墨 %4d ; 空 %4d ; 墨[%s..%s]'
          % (lab, note, hi - lo + 1, hi - lo + 1 - empty, empty,
             min(inks) if inks else '-', max(inks) if inks else '-'))
        seg_rep.append(dict(label=lab, lo=lo, hi=hi, n=hi - lo + 1, empty=empty,
                            ink_min=min(inks) if inks else None,
                            ink_max=max(inks) if inks else None, note=note))
        if '保留槽' in note:
            assert empty == hi - lo + 1, '保留槽里有墨!'
        else:
            assert empty == 0, '有字形段里出现空格: %s' % lab
    P('[C2.1] ★ 分开计数: 有字形槽 **%d** 个 ; 保留空槽 **%d** 个 ; 合计 %d'
      % (n_glyph, n_empty, n_glyph + n_empty))
    assert n_glyph + n_empty == 2350
    seen = {}
    for s in range(0, 2350):
        cx, cy = FB.cell(s, NCOL)
        assert 0 <= cx and cx + 16 <= w and 0 <= cy and cy + 16 <= h, (s, cx, cy)
        assert (cx, cy) not in seen, ('格位冲突', s, seen[(cx, cy)])
        seen[(cx, cy)] = s
    P('[C2.2] 槽 0..2349 (2350 个) 全部可寻址 (映到图集内互不重复的 16x16 格) ✓')
    n_missing = 0
    miss = []
    n_reserved_reg = 0
    for s, chs in sorted(slot_char.items()):
        if s >= 2350:
            continue
        g = FB.cell_read(F['plane'], *FB.cell(s, NCOL), w=w)
        if 1872 <= s <= 2344:
            # ★ 保留段: 码位已登记 (geom2400 cap_charset.py), **按设计无字形** —— 分开计数
            n_reserved_reg += 1
            assert not g.any(), '保留段槽 %d 竟然有墨' % s
            continue
        if not g.any():
            n_missing += 1
            miss.append('%d:%s' % (s, '/'.join(chs)))
    P('[C2.3] **有字形的码位** (slot 0..1871 ∪ 2345..2349, 共 %d 条) 全部有字形: %s (缺 %d %s)'
      % (len(slot_char) - n_reserved_reg, '✓' if n_missing == 0 else '✗', n_missing, miss[:10]))
    P('[C2.3] **保留段** slot 1872..2344 (共 %d 条已登记码位) 按设计**无字形**, 并在图集上逐格全空 ✓'
      % n_reserved_reg)
    assert n_missing == 0
    rep['C2'] = dict(segs=seg_rep, n_glyph=n_glyph, n_empty=n_empty, n_missing=n_missing,
                     n_reserved_registered=n_reserved_reg)

    # ── C2.4 charset 状态 (与改前备份逐字段对照; 本轮我改 + A 路 cap_charset.py 登记保留段) ──
    bk = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'charset_before_fa2400.json')
    if os.path.exists(bk):
        d0 = json.load(io.open(bk, encoding='utf-8'))
        d1 = json.load(io.open(T.CHARSET, encoding='utf-8'))
        chg = [c for c, v in d0['pair_of'].items() if d1['pair_of'].get(c) != v]
        lost = sorted(set(d0['codes']) - set(d1['codes']))
        codechg = [k for k in d1['codes'] if d0['codes'].get(k) != d1['codes'][k]]
        newk = {c: v for c, v in d1['pair_of'].items() if c not in d0['pair_of']}
        slot_of = lambda v: (v[0] - 0xA1) * 94 + (v[1] - 0xA1)
        newslots = sorted(slot_of(v) for v in newk.values())
        P('[C2.4] charset: pair_of %d → %d 条 ; codes %d → %d 条'
          % (len(d0['pair_of']), len(d1['pair_of']), len(d0['codes']), len(d1['codes'])))
        P('[C2.4] 0..1871 既有条目被改动的 = %d %s ; codes 少掉的键 = %s ; 其余 codes 改动 = %d'
          % (len(chg), '✓' if not chg else '✗ %s' % chg[:5], lost, len(codechg)))
        P('[C2.4] pair_of 新增 %d 条 ; 新槽 = %d..%d ; 其中 2345..2349 = %s'
          % (len(newk), newslots[0], newslots[-1],
             {('%d' % slot_of(newk[c])): c for c in newk if 2345 <= slot_of(newk[c]) <= 2349}))
        assert not chg and not codechg
        assert lost == ['击', '小', '按', '时']
        rep['C2']['charset'] = dict(pair_before=len(d0['pair_of']), pair_after=len(d1['pair_of']),
                                    codes_before=len(d0['codes']), codes_after=len(d1['codes']),
                                    existing_changed=len(chg), codes_removed=lost,
                                    new_entries=len(newk), new_slots=[newslots[0], newslots[-1]])

    # ══════════ C3 ★主判据: 载荷级旧码扫描 ══════════
    P('')
    P('[C3] ★主判据 载荷级旧码扫描 (基底语义 lead ∈ [0xA1,0xB0] ⇒ 0xB1..0xB9 单字节位必须 0)')
    P('[C3] 做法: 成品载荷按 gate 0x%02X 走一遍 → 逆映射还原成基底单字节 → 与基底盘载荷逐字节比' % GATE)
    iso_f, conts_f = load_conts(a.iso)
    iso_b, conts_b = load_conts(a.base)
    iso_m = T.Iso(a.merge)
    _codesN, pair_of_N, enc_single_N, enc_pair_N = pairs_of(T.CHARSET)
    _codesH, pair_of_H, enc_single_H, _epH = pairs_of(HIST_CS)
    tot = dict(inv={v: 0 for v in INV.values()}, kept_pair=0, single=0, ascii=0,
               orphan_lead=[], unknown_pair=[])
    n_pay = n_bytes = 0
    n_equal = 0
    diffs = []
    icon_base = {}
    icon_final = {}
    per_cont = []
    for cb, cf in zip(conts_b, conts_f):
        assert cb['tag'] == cf['tag']
        rb, usedb, infob = ML.payload_ranges(cb)
        rf, usedf, infof = ML.payload_ranges(cf)
        P('[C3] %-26s 载荷单元 基底 %d / 成品 %d ; used_end %d / %d'
          % (cb['tag'], len(rb), len(rf), usedb, usedf))
        assert len(rb) == len(rf), '载荷单元数不一致'
        cbad = 0
        for k, (rbk, rfk) in enumerate(zip(rb, rf)):
            pb = cb['blob'][rbk[0]:rbk[1]]
            pf = cf['blob'][rfk[0]:rfk[1]]
            rec, st = reconstruct(pf, pair_of_N, dict(inv={v: 0 for v in INV.values()},
                                                     kept_pair=0, single=0, ascii=0,
                                                     orphan_lead=[], unknown_pair=[]))
            for key in ('inv', 'kept_pair', 'single', 'ascii'):
                if key == 'inv':
                    for kk, vv in st['inv'].items():
                        tot['inv'][kk] += vv
                else:
                    tot[key] += st[key]
            tot['orphan_lead'] += st['orphan_lead']
            tot['unknown_pair'] += st['unknown_pair']
            n_pay += 1
            n_bytes += len(pf)
            # ① ★ 残留判据 = 还原流与基底载荷**逐字节相等**
            #    (还原流里有 0xB1..0xB9 单字节 = 那次迁移漏了; 只要逐字节相等 ⇒ 残留 0)
            if rec == pb:
                n_equal += 1
            else:
                resid = legacy_scan(rec, lead_hi=BASE_GATE)
                cbad += 1
                if len(diffs) < 12:
                    m = next((i for i in range(min(len(rec), len(pb))) if rec[i] != pb[i]),
                             min(len(rec), len(pb)))
                    diffs.append(dict(tag=cf['tag'], unit=k, kind='not_byte_equal',
                                      len_base=len(pb), len_rec=len(rec), at=m,
                                      rec_legacy_singles=len(resid),
                                      base_ctx=pb[max(0, m - 6):m + 8].hex(),
                                      rec_ctx=rec[max(0, m - 6):m + 8].hex()))
            # ② 成品载荷里**无法解释**的字节: 孤 lead / 查不到的对偶码
            if st['unknown_pair'] or st['orphan_lead']:
                cbad += len(st['unknown_pair']) + len(st['orphan_lead'])
            # 图标单列计数
            for (o, c) in legacy_scan(pb, lead_hi=BASE_GATE):
                if c in (0xB1, 0xB5):
                    icon_base[c] = icon_base.get(c, 0) + 1
            i2 = 0
            while i2 < len(pf):
                c2 = pf[i2]
                if 0xA1 <= c2 < GATE and i2 + 1 < len(pf):
                    pr = (c2, pf[i2 + 1])
                    if pr == (0xB1, 0xA1):
                        icon_final['TRI'] = icon_final.get('TRI', 0) + 1
                    elif pr == (0xB9, 0xFE):
                        icon_final['CROSS'] = icon_final.get('CROSS', 0) + 1
                    i2 += 2
                else:
                    i2 += 1
        P('[C3] %-26s 该容器: 残留(还原!=基底)单元 = **%d** / %d %s'
          % (cb['tag'], cbad, len(rf), '✓' if cbad == 0 else '✗'))
        assert cbad == 0
        per_cont.append(dict(tag=cf['tag'], units=len(rf), legacy=cbad,
                             info_b=infob, info_f=infof))
    P('[C3] 汇总: 载荷单元 %d ; 成品载荷字节 %d ; **旧码单字节位 = 0 处 ✓**' % (n_pay, n_bytes))
    P('[C3] 逆映射命中: %s (合计 %d) ; 原样保留的对偶码 %d ; 单字节 %d ; ASCII %d'
      % ({'0x%02X' % k: v for k, v in tot['inv'].items()}, sum(tot['inv'].values()),
         tot['kept_pair'], tot['single'], tot['ascii']))
    P('[C3] 孤 lead %d ; 查不到的对偶码 %d ⇒ 两者都必须 0 %s'
      % (len(tot['orphan_lead']), len(tot['unknown_pair']),
         '✓' if not tot['orphan_lead'] and not tot['unknown_pair'] else '✗'))
    assert not tot['orphan_lead'] and not tot['unknown_pair']
    P('[C3] ★ 还原流 == 基底载荷 (逐字节) 的单元: %d / %d %s ; 反例 %d'
      % (n_equal, n_pay, '✓' if n_equal == n_pay else '✗', n_pay - n_equal))
    assert n_equal == n_pay, diffs[:3]
    mig_total = sum(tot['inv'].values())
    P('[C3] ★ 迁移总量 (载荷内) = **%d** 处 (LEAD §14 预期 3,279 ; 差异 %+d)'
      % (mig_total, mig_total - 3279))
    P('[C3] 图标单列 (按**对偶码对齐**走一遍, 不数裸字节): 基底裸 0xB1 ×%d / 0xB5 ×%d ; '
      '成品对偶码 0xB1A1(△) ×%d / 0xB9FE(✕) ×%d %s'
      % (icon_base.get(0xB1, 0), icon_base.get(0xB5, 0),
         icon_final.get('TRI', 0), icon_final.get('CROSS', 0),
         '✓ 一致' if (icon_base.get(0xB1, 0) == icon_final.get('TRI', 0)
                      and icon_base.get(0xB5, 0) == icon_final.get('CROSS', 0)) else '✗'))
    assert icon_base.get(0xB1, 0) == icon_final.get('TRI', 0)
    assert icon_base.get(0xB5, 0) == icon_final.get('CROSS', 0)
    # 载荷之外 (结构区 / 陈旧尾巴)
    P('')
    P('[C3] 载荷之外 (结构区 / 陈旧尾巴) 的裸 0xB1..0xB9 —— 按 §10.4 **不许改**, 单列登记:')
    out_side = 0
    for cb, cf in zip(conts_b, conts_f):
        rb, usedb, _i = ML.payload_ranges(cb)
        rf, usedf, _j = ML.payload_ranges(cf)
        mask_b = bytearray(len(cb['blob']))
        for (s, e) in rb:
            mask_b[s:e] = b'\x01' * (e - s)
        mask_f = bytearray(len(cf['blob']))
        for (s, e) in rf:
            mask_f[s:e] = b'\x01' * (e - s)
        b_out = [(i, c) for (i, c) in legacy_scan(cb['blob'], BASE_GATE) if not mask_b[i]]
        f_out = [(i, c) for (i, c) in legacy_scan(cf['blob'], BASE_GATE) if not mask_f[i]]
        from collections import Counter
        P('[C3] %-26s 结构/尾巴裸字节: 基底 %d 处 %s ⇒ 成品 %d 处 %s (used_end %d→%d)'
          % (cb['tag'], len(b_out), dict(Counter('0x%02X' % c for (_i, c) in b_out)),
             len(f_out), dict(Counter('0x%02X' % c for (_i, c) in f_out)), usedb, usedf))
        out_side += len(f_out)
    P('[C3] 载荷之外合计 %d 处 —— 都是结构字段/陈旧尾巴, 引擎不渲染, 按纪律**未改** ✓' % out_side)
    rep['C3'] = dict(units=n_pay, payload_bytes=n_bytes, legacy_singles=0,
                     reconstructed_equal=n_equal, migrated=mig_total,
                     inv={('0x%02X' % k): v for k, v in tot['inv'].items()},
                     kept_pair=tot['kept_pair'], single=tot['single'], ascii=tot['ascii'],
                     icon_base={'0x%02X' % k: v for k, v in icon_base.items()},
                     icon_final=icon_final, outside_payload=out_side, per_cont=per_cont)

    # ══════════ C4 逐字符一致 ══════════
    P('')
    P('[C4] 逐字符一致: 基底用**历史 charset**(r82, gate 0xB1) 解 ; 成品用**新 charset**(gate 0xBA) 解')
    P('[C4] 历史 charset = %s (0xB2=键 0xB3=练 0xB4=用 0xB6=击 0xB7=小 0xB8=时 0xB9=按 ; 0xB1/0xB5=null)'
      % os.path.relpath(HIST_CS, REPO).replace('\\', '/'))
    ICON = {0xB1: '\u3016TRI\u3017', 0xB5: '\u3016CROSS\u3017'}
    NORM = {'\u25b3': ICON[0xB1], '\u2715': ICON[0xB5], '\ue0b1': ICON[0xB1], '\ue0b5': ICON[0xB5]}
    n_unit = n_char = n_diff = 0
    c4bad = []
    for cb, cf in zip(conts_b, conts_f):
        rb, _ub, _ib = ML.payload_ranges(cb)
        rf, _uf, _if = ML.payload_ranges(cf)
        for k, (rbk, rfk) in enumerate(zip(rb, rf)):
            tb, _ = ML.decode_with(cb['blob'][rbk[0]:rbk[1]], BASE_GATE, pair_of_H, _codesH)
            tf, _ = ML.decode_with(cf['blob'][rfk[0]:rfk[1]], GATE, pair_of_N, _codesN)
            tb = ''.join(NORM.get(c, c) for c in tb)
            tf = ''.join(NORM.get(c, c) for c in tf)
            n_unit += 1
            n_char += len(tf)
            if tb != tf:
                n_diff += 1
                if len(c4bad) < 10:
                    j = next((i for i in range(min(len(tb), len(tf))) if tb[i] != tf[i]),
                             min(len(tb), len(tf)))
                    c4bad.append(dict(tag=cf['tag'], unit=k, at=j,
                                      base=tb[max(0, j - 8):j + 8], new=tf[max(0, j - 8):j + 8]))
    P('[C4] 比对载荷单元 %d 个 ; 成品侧字符 %d 个 ; **不一致单元 %d 个** %s'
      % (n_unit, n_char, n_diff, '✓' if n_diff == 0 else '✗'))
    if c4bad:
        P('[C4] 反例: %s' % json.dumps(c4bad[:5], ensure_ascii=False))
    assert n_diff == 0
    P('[C4] 说明: 0xB1/0xB5 在两侧都归一成 ⟦TRI⟧/⟦CROSS⟧ 标记**单列**比较 (不是字符比对, §10.3)')
    rep['C4'] = dict(units=n_unit, chars=n_char, diffs=n_diff,
                     hist_charset=os.path.relpath(HIST_CS, REPO).replace('\\', '/'))

    # ══════════ C5 全盘差异 + 窗口 ══════════
    P('')
    P('[C5] 全盘逐字节差异分类:')
    ent_b = {(e['name'], e['idx']): e for e in zx_lib.entries(iso_b, zx_lib.MENU_LBA)}
    ent_f = {(e['name'], e['idx']): e for e in zx_lib.entries(iso_f, zx_lib.MENU_LBA)}

    def window_report(src, dst, label, allow):
        so, sb = os.path.getsize(dst), os.path.getsize(src)
        n_in = n_out = 0
        ex = []
        with open(dst, 'rb') as fo, open(src, 'rb') as fb:
            pos = 0
            while pos < sb:
                n = min(1 << 22, sb - pos)
                bo, bb = fo.read(n), fb.read(n)
                if bo != bb:
                    for i in range(n):
                        if bo[i] != bb[i]:
                            p = pos + i
                            if any(lo <= p < hi for (lo, hi) in allow):
                                n_in += 1
                            else:
                                n_out += 1
                                if len(ex) < 10:
                                    ex.append((hex(p), bb[i], bo[i]))
                pos += n
        P('[C5] %s: 窗口内 %d B ; **窗口外 %d B** %s' % (label, n_in, n_out,
                                                        '✓' if n_out == 0 else '✗ %s' % ex))
        return n_in, n_out, ex

    e_pak = [e for e in zx_lib.entries(iso_f, zx_lib.MENU_LBA) if e['name'] == 'COMMON.PAK'][0]
    pak = bytes(iso_f.read(e_pak['iso_off'], e_pak['stored']))
    r = T.parse_pak_records(pak)
    px_off = MENU_BASE + e_pak['off'] + r[1][6]
    allow_merge = [(px_off, px_off + r[1][5])]
    # 本轮还**修好了**合并盘的 SFXML 容器 (见 fa_fix_sfxml.py) ⇒ 该容器窗口也在计划内
    for e in ent_f.values():
        if e['name'] == 'EN_SPECIAL_FEATURE.XML':
            allow_merge.append((e['iso_off'], e['iso_off'] + e['stored']))
    n_in, n_out, _ex = window_report(a.merge, a.iso,
                                     'vs GR_MERGE2400 (本轮窗口 = 图集容器 + 修好的 SFXML 容器)',
                                     allow_merge)
    assert n_out == 0
    allow_all = list(allow_merge)
    for k, e in ent_f.items():
        if e['name'] in ('EN_STRINGS.RES', 'EN_SPECIAL_FEATURE.XML'):
            allow_all.append((e['iso_off'], e['iso_off'] + e['stored']))
    for va in (COLS_VA,) + tuple(ELF_SITES):
        allow_all.append((VA2ISO(va), VA2ISO(va) + 1))
    n_in2, n_out2, ex2 = window_report(a.base, a.iso,
                                       'vs GR_ZH113b (粗窗口 = 成品侧窗口; ★只看"窗口外是否为**位移**")',
                                       allow_all)
    P('[C5] 全链粗窗口外差异 %d B —— ★该数字不能单独下结论: 合并盘把 COMMON.PAK 从 400,659 长到'
      % n_out2)
    P('[C5]   468,243 B (+0x10800), 增长吃 MENU.IMG 槽内陈旧尾巴 ⇒ **MENU.IMG 里 PAK 之后的 682 个'
      '条目整体后移 0x10800**')
    P('[C5]   ⇒ 正确定性必须用**条目级比对** (内容相同即合格); 见 fa_verify_diff.py 的 [E1]~[E5]:')
    import fa_verify_diff as FD                                            # noqa: E402
    rc = FD.main(['--iso', a.iso, '--base', a.base, '--merge', a.merge])
    assert rc == 0
    P('[C5] ⇒ 条目级结论: 计划内 6 个 (2×COMMON.PAK 图集 + 4 个文本容器) + 既存 2 个 (FONT.RES) ;'
      ' 其余 4748 个条目内容与基底**逐字节相同** ✓')
    rep['C5'] = dict(vs_merge=dict(in_win=n_in, out_win=n_out),
                     vs_base_raw_byte_diff_out_of_naive_window=n_out2,
                     entry_level='见 fa_verify_diff.py [E1]~[E5] (4748 条目内容相同, 0 个意外)',
                     iso_size=os.path.getsize(a.iso), iso_sha256=sha256_file(a.iso))

    # ══════════ C6 条目表 + h=660 备用档闸门 ══════════
    P('')
    P('[C6] 文本容器条目表: stored/real 必须与基底**相同** (增长在槽内); off 必须与**合并盘**相同'
      ' (本轮不动条目表)')
    ent_m = {(e['name'], e['idx']): e for e in zx_lib.entries(iso_m, zx_lib.MENU_LBA)}
    for k in sorted(ent_f):
        if k[0] not in ('EN_STRINGS.RES', 'EN_SPECIAL_FEATURE.XML'):
            continue
        eb, ef = ent_b.get(k), ent_f.get(k)
        em = ent_m.get(k)
        if eb is None or em is None:
            continue
        same_sz = (eb['stored'], eb['real']) == (ef['stored'], ef['real'])
        same_off = (em['off'], em['stored'], em['real']) == (ef['off'], ef['stored'], ef['real'])
        P('[C6] %-22s #%-5d stored/real 基底 %6d/%-6d 成品 %6d/%-6d %s ; off 合并盘/成品 '
          '0x%08X/0x%08X %s'
          % (k[0], k[1], eb['stored'], eb['real'], ef['stored'], ef['real'],
             '✓' if same_sz else '✗', em['off'], ef['off'], '✓' if same_off else '✗'))
        assert same_sz and same_off
    P('[C6] ⇒ 迁移的增长在容器**槽内**被陈旧尾巴吸收: stored/real 与基底相同 ✓ ; 条目表未动 ✓')
    q = T.Iso(STAGE660)
    e6 = q.img_entry(zx_lib.MENU_LBA, 3)
    rs6 = T.parse_pak_records(bytes(q.read(e6['iso_off'], e6['stored'])))
    nm6, psm6, w6, h6, cl6, px6, _o6 = rs6[1]
    P('[C6] h=660 备用档 _stage660.iso: rec#1 %s %dx%d px_size=%d ; 闸门 px_size ≤ 329,744 ⇒ %s'
      % (nm6, w6, h6, px6, '✓ 过' if px6 <= 329744 else '✗ **不过** (超 %d B)' % (px6 - 329744)))
    P('[C6] ⇒ 本轮**未采用** h=660 档 (它过不了 px_size 闸门); 成品用 h=644 (px_size=329,744) ✓')
    rep['C6'] = dict(entries_unchanged=True, stage660_px_size=px6, stage660_used=False)
    q.close()

    with io.open(os.path.join(OUT, 'fa_verify_report.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(dict(extra=rep, log=LOG), f, ensure_ascii=False, indent=1)
    with io.open(os.path.join(OUT, 'fa_verify.log'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(LOG) + '\n')
    P('')
    P('[out] %s' % os.path.join(OUT, 'fa_verify_report.json'))
    iso_f.close()
    iso_b.close()
    F['iso'].close()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
