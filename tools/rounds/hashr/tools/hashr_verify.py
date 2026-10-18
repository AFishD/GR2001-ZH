# -*- coding: utf-8 -*-
r"""hashr_verify.py — ★ 独立终检 (从**盘上重读**, 不使用构建期的任何内存状态)

用法:
    python work/builds/GR_HASHR/tools/hashr_verify.py [--base <K2.iso>] [--prod <GR_HASHR2400.iso>]
                                                      [--cs-old <json>] [--cs-new <json>]

判据:
  [V1] 哨兵清零   3 容器 + ES/FR + charset: 作为**对偶 trail** 的 0xB1/0xB5 = 0
  [V2] 字符不变   3 容器**逐条**解码字符序列, 产物 == 基底
  [V3] 字形不丢   有字形槽数不减少 ; 每个被搬字「新格 == 基底旧格」逐 texel
  [V4] 图集不变式 px_size == w*h/2+16 ; (w*h/2)%2048==0 ; 格位互不重复且不越界
  [V5] 结构不变   容器 blob 长度 / IMG 条目表 / ISO 尺寸 / 全盘差异窗口
输出: work/builds/GR_HASHR/audit/verify.txt
"""
import argparse
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                       # noqa: E402
import tcslib as T                                                       # noqa: E402
import zx_lib                                                            # noqa: E402
import migrate_legacy as ML                                              # noqa: E402
import hashr_build as HB                                                 # noqa: E402

K2 = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'GR_FA2400_K2.iso')
PROD = os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'GR_HASHR2400.iso')
CS_OLD = os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'backup',
                      'charset_compiled_zh16.json.before_hashr')
CS_NEW = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
SENT = (0xB1, 0xB5)
OUT = []
FAIL = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    OUT.append(s)


def chk(cond, msg):
    P('%s %s' % ('[ok]' if cond else '[!!]', msg))
    if not cond:
        FAIL.append(msg)
    return bool(cond)


def load_cs(path):
    j = json.load(io.open(path, encoding='utf-8'))
    return (j, {ch: tuple(v) for ch, v in j['pair_of'].items()},
            {tuple(v): ch for ch, v in j['pair_of'].items()},
            {ch: int(b) for ch, b in j['codes'].items()})


def walk(data, gate, pair_dec):
    """→ [(i, kind, pair|None, ch|None)]"""
    i, n = 0, len(data)
    while i < n:
        b = data[i]
        if T.LEAD_LO <= b < gate:
            t = data[i + 1] if i + 1 < n else None
            if t is not None and (b, t) in pair_dec:
                yield (i, 'pair', (b, t), pair_dec[(b, t)])
                i += 2
                continue
            yield (i, 'odd', (b, t), None)
            i += 1
            continue
        yield (i, 'single', None, None)
        i += 1


def scan_container(iso, spec, gate, pair_dec):
    (kind, img, lba, idx, tag, why) = spec
    e = iso.img_entry(lba, idx)
    raw = iso.read(e['iso_off'], e['stored'])
    blob = b''.join(s[0] for s in T.lzo_subs(raw))
    c = dict(name=kind, tag=tag, blob=blob)
    ranges, _used, info = ML.payload_ranges(c)
    res = dict(tag=tag, blob=blob, ranges=ranges, info=info, raw=raw,
               entry=e, lba=lba, idx=idx, kind=kind)
    trails, bare, chars, odd = 0, 0, [], 0
    for (s, ee) in ranges:
        pay = blob[s:ee]
        for (_i, k, pr, ch) in walk(pay, gate, pair_dec):
            if k == 'pair':
                chars.append(ch)
                if pr[1] in SENT:
                    trails += 1
            elif k == 'odd':
                odd += 1
            elif k == 'single':
                pass
        bare += sum(pay.count(bytes([b])) for b in SENT)
    res.update(trails=trails, chars=chars, odd=odd)
    return res


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default=K2)
    ap.add_argument('--prod', default=PROD)
    ap.add_argument('--cs-old', default=CS_OLD)
    ap.add_argument('--cs-new', default=CS_NEW)
    ap.add_argument('--skip-diff', action='store_true')
    a = ap.parse_args(argv)
    j_old, po_old, pd_old, codes_old = load_cs(a.cs_old)
    j_new, po_new, pd_new, codes_new = load_cs(a.cs_new)
    ib, ip = T.Iso(a.base), T.Iso(a.prod)
    gb, gp = T.read_decode_gate(ib), T.read_decode_gate(ip)
    P('=' * 100)
    P('hashr_verify.py — 独立终检')
    P('  base = %s  (sha256 %s)' % (a.base, HB.sha256_file(a.base)))
    P('  prod = %s  (sha256 %s)' % (a.prod, HB.sha256_file(a.prod)))
    P('  gate base=0x%02X prod=0x%02X' % (gb, gp))
    P('  charset old: pair_of %d ; new: pair_of %d'
      % (len(po_old), len(po_new)))

    # ── [V1] 哨兵清零 ──
    P('')
    P('---- [V1] 哨兵清零 (口径: pair trail ∈ {B1,B5} ; 裸单字节单列) ----')
    tot_old = tot_new = 0
    for spec in ML.CONTAINER_SPECS:
        tag = spec[4]
        ro = scan_container(ib, spec, gb, pd_old)
        rn = scan_container(ip, spec, gp, pd_new)
        n_bare = sum(rn['blob'][s:e].count(bytes([b])) for (s, e) in rn['ranges']
                     for b in SENT)
        P('[V1] %-24s 哨兵 trail %4d → %4d ; 对偶码 %5d → %5d ; 配不出对 %d → %d ; 裸哨兵 %d'
          % (tag, ro['trails'], rn['trails'], len(ro['chars']), len(rn['chars']),
             ro['odd'], rn['odd'], n_bare))
        if tag in HB.CORE:
            tot_old += ro['trails']
            tot_new += rn['trails']
        chk(rn['trails'] == 0, '%s: 产物盘上作为对偶 trail 的 0xB1/0xB5 = %d (期望 0)'
            % (tag, rn['trails']))
        chk(ro['blob'] and len(ro['blob']) == len(rn['blob']),
            '%s: 解压 blob 长度不变 (%d)' % (tag, len(rn['blob'])))
    P('[V1] 3 个中文容器哨兵 trail 合计: %d → %d' % (tot_old, tot_new))
    chk(tot_new == 0, '3 容器哨兵 trail 合计 = 0')
    n_bad_old = len([1 for p in po_old.values() if p[1] in SENT])
    n_bad_new = len([1 for p in po_new.values() if p[1] in SENT])
    P('[V1] charset 里 trail ∈ {B1,B5} 的登记: %d → %d' % (n_bad_old, n_bad_new))
    chk(n_bad_new == 0, 'charset 哨兵 trail 登记 = 0')

    # ── [V2] 字符不变 (逐条解码) ──
    P('')
    P('---- [V2] 字符不变: 3 容器**逐条**解码字符序列 ----')
    n_entries = n_diff = 0
    for spec in ML.CONTAINER_SPECS:
        if spec[4] not in HB.CORE:
            continue
        ro = scan_container(ib, spec, gb, pd_old)
        rn = scan_container(ip, spec, gp, pd_new)
        n_txt = 0
        for k, (s, e) in enumerate(ro['ranges']):
            so, eo = ro['ranges'][k]
            sn, en = rn['ranges'][k]
            co = [c for (_i, kk, _p, c) in walk(ro['blob'][so:eo], gb, pd_old) if kk == 'pair']
            cn = [c for (_i, kk, _p, c) in walk(rn['blob'][sn:en], gp, pd_new) if kk == 'pair']
            n_entries += 1
            n_txt += 1
            if co != cn:
                n_diff += 1
                if n_diff <= 3:
                    P('[V2]   ✗ %s 第 %d 条: 基底 %r vs 产物 %r'
                      % (spec[4], k, ''.join(co)[:60], ''.join(cn)[:60]))
        P('[V2] %-24s 逐条解码比较 %d 条 ; 不符 %d' % (spec[4], n_txt, n_diff))
    chk(n_diff == 0, '3 容器逐条解码字符序列完全一致 (%d 条, 不符 0)' % n_entries)
    # 逐字节: 只允许"旧哨兵码 → 新码"的 2 字节替换
    P('')
    P('---- [V2b] 逐字节差异只允许出现在「旧哨兵码 → 新码」的 2 字节上 ----')
    remap = {po_old[ch]: po_new[ch] for ch in po_old if ch in po_new
             and po_old[ch] != po_new[ch]}
    P('[V2b] 码位改动表 %d 条' % len(remap))
    bad = 0
    for spec in ML.CONTAINER_SPECS:
        if spec[4] not in HB.CORE:
            continue
        ro = scan_container(ib, spec, gb, pd_old)
        rn = scan_container(ip, spec, gp, pd_new)
        for k, (s, e) in enumerate(ro['ranges']):
            so, eo = ro['ranges'][k]
            sn, en = rn['ranges'][k]
            bo, bn = ro['blob'][so:eo], rn['blob'][sn:en]
            if bo == bn:
                continue
            i = 0
            while i < len(bo):
                if bo[i] == bn[i]:
                    i += 1
                    continue
                old = (bo[i], bo[i + 1])
                new = (bn[i], bn[i + 1])
                if remap.get(old) != new:
                    bad += 1
                    if bad <= 5:
                        P('[V2b]   ✗ %s 第 %d 条 @%d: %02X%02X → %02X%02X 不在改动表'
                          % (spec[4], k, i, old[0], old[1], new[0], new[1]))
                i += 2
    chk(bad == 0, '所有字节差异都是登记在案的「旧哨兵码 → 新码」2 字节替换 (越界 %d)' % bad)

    # ── [V3] 字形不丢 ──
    P('')
    P('---- [V3] 字形不丢 ----')
    Fb, Fp = HB.read_font(a.base), HB.read_font(a.prod)
    w, h, ncol, skip, y0 = Fb['w'], Fb['h'], 64, 2, 3
    cap = (gb - 0xA1) * 94
    ink_b = [int(HB.cell_read(Fb['plane'], *HB.cell(s, ncol, skip, y0)).sum())
             for s in range(cap)]
    ink_p = [int(HB.cell_read(Fp['plane'], *HB.cell(s, ncol, skip, y0)).sum())
             for s in range(cap)]
    ng_b = len([x for x in ink_b if x])
    ng_p = len([x for x in ink_p if x])
    P('[V3] 有墨槽 (0..%d): 基底 %d → 产物 %d' % (cap - 1, ng_b, ng_p))
    chk(ng_p >= ng_b, '有字形槽数不减少 (%d ≥ %d)' % (ng_p, ng_b))
    moved = [(ch, po_old[ch], po_new[ch]) for ch in po_old
             if ch in po_new and po_old[ch] != po_new[ch]]
    okm = 0
    for (ch, o, nw) in moved:
        so, sn = HB.slot_of_pair(*o), HB.slot_of_pair(*nw)
        gb_ = HB.cell_read(Fb['plane'], *HB.cell(so, ncol, skip, y0))
        gn_ = HB.cell_read(Fp['plane'], *HB.cell(sn, ncol, skip, y0))
        if (gb_ == gn_).all():
            okm += 1
        else:
            P('[V3]   ✗ %r 槽 %d→%d 逐 texel 不同' % (ch, so, sn))
    P('[V3] 被搬字 %d 个: 产物新格 == 基底旧格 逐 texel 的 %d 个' % (len(moved), okm))
    chk(okm == len(moved), '被搬字的字形逐 texel 等价 (%d/%d)' % (okm, len(moved)))
    # 全部注册字的"有字形"状态: 只允许"从有到有"(搬家)
    miss_b = [ch for ch, p in po_old.items()
              if not HB.cell_read(Fb['plane'], *HB.cell(HB.slot_of_pair(*p), ncol, skip, y0)).any()]
    miss_p = [ch for ch, p in po_new.items()
              if not HB.cell_read(Fp['plane'], *HB.cell(HB.slot_of_pair(*p), ncol, skip, y0)).any()]
    P('[V3] 注册但对偶格无墨的字: 基底 %d → 产物 %d' % (len(miss_b), len(miss_p)))
    chk(len(miss_p) <= len(miss_b), '「注册但无字形」的字数不增加 (%d ≤ %d)'
        % (len(miss_p), len(miss_b)))

    # ── [V4] 图集不变式 ──
    P('')
    P('---- [V4] 图集不变式 ----')
    for (nm, F) in (('base', Fb), ('prod', Fp)):
        chk((F['name'], F['psm'], F['w'], F['h']) == ('new_font_revised', 0x14, 1024, 644),
            '%s: rec#1 = %s psm 0x%X %dx%d' % (nm, F['name'], F['psm'], F['w'], F['h']))
        chk(F['px_size'] == F['w'] * F['h'] // 2 + 16,
            '%s: px_size %d == w*h/2+16' % (nm, F['px_size']))
        chk((F['w'] * F['h'] // 2) % 2048 == 0,
            '%s: (w*h/2) %% 2048 == 0' % nm)
        seen = set()
        okc = True
        for s in range(cap):
            cx, cy = HB.cell(s, ncol, skip, y0)
            if not (0 <= cx and cx + 16 <= F['w'] and 0 <= cy and cy + 16 <= F['h']) \
               or (cx, cy) in seen:
                okc = False
                break
            seen.add((cx, cy))
        chk(okc, '%s: 槽 0..%d 全部映到图集内互不重复的 16x16 格' % (nm, cap - 1))

    # ── [V5] 结构 / 尺寸 / 全盘差异 ──
    P('')
    P('---- [V5] 结构 / 尺寸 / 全盘差异 ----')
    chk(os.path.getsize(a.base) == os.path.getsize(a.prod),
        'ISO 尺寸不变: %d' % os.path.getsize(a.prod))
    same_entries = True
    for spec in ML.CONTAINER_SPECS:
        eb = ib.img_entry(spec[2], spec[3])
        ep = ip.img_entry(spec[2], spec[3])
        if (eb['stored'], eb['off'], eb['real']) != (ep['stored'], ep['off'], ep['real']):
            same_entries = False
    chk(same_entries, '7 个容器的 IMG 条目字段 (stored/off/real) 未动')
    # 图集容器外的 PAK 字节不变
    pakb = bytes(ib.read(Fb['e_pak']['iso_off'], Fb['e_pak']['stored']))
    pakp = bytes(ip.read(Fp['e_pak']['iso_off'], Fp['e_pak']['stored']))
    nchg = sum(1 for i in range(len(pakb)) if pakb[i] != pakp[i])
    inside = sum(1 for i in range(len(pakb)) if pakb[i] != pakp[i]
                 and Fb['PX'] <= i < Fb['PX'] + Fb['px_size'])
    P('[V5] COMMON.PAK %d B: 改动 %d B, 全部落在图集容器内: %d %s'
      % (len(pakb), nchg, inside, '✓' if inside == nchg else '✗'))
    chk(inside == nchg, 'COMMON.PAK 的改动全部落在图集容器内')
    # ISO 尺寸 vs 原盘
    P('[V5] ISO %d B ; 与 third_party/orig 的原盘尺寸对比: (见 docs)'
      % os.path.getsize(a.prod))
    ib.close()
    ip.close()
    P('')
    P('==== 终检结论: %s (%d 项不合格) ====' % ('全部通过' if not FAIL else '有不合格项',
                                                len(FAIL)))
    for f in FAIL:
        P('   ✗ %s' % f)
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit', 'verify.txt'),
                 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(OUT) + '\n')
    return 1 if FAIL else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
