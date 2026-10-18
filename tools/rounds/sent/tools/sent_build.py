# -*- coding: utf-8 -*-
r"""sent_build.py —— 候选 R（0xB1/0xB5 图标哨兵）对照盘构建。

基底一律 = work\builds\GR_CVAR\CVAR_04_text.iso（已实证会崩的最小复现盘；只读）。

四张盘（每张单变量）：
  SENT_01_trail_fix.iso      3 个容器里**所有**「对偶码 trail ∈ {0xB1,0xB5}」的字**整对搬移**
                             到「安全且空闲」的对偶码（两个字节都不再是哨兵）；其余一字不动。
                             LANG 286 处 + XML 158 处。
  SENT_02_icon_path_off.iso  只改原盘 ELF：把 DrawString 里对 0xB1/0xB5 的**全部图标特判立即数**
                             改成永不命中（`addiu rX,zero,0xFFB5/0xFFB1` → `…,0xFF00`）；
                             文本/图集/结构一字不动。⇒ 等价于「关掉图标路径」。
  SENT_03_xml_only.iso       只搬移 XML 的 158 处哨兵（LANG 原样保留）。
  SENT_04_lang_only.iso      只搬移两个 LANG 容器的 286 处哨兵（XML 原样保留）。
  （SENT_03 + SENT_04 与 SENT_01 构成 {LANG,XML}×{改,不改} 的 2×2 闭合）

只读：基底 ISO（mmap）与英文原盘（只读）。写：work\builds\GR_SENT\**。
"""
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sent_lib as L                                                     # noqa: E402
import tcslib as T                                                       # noqa: E402
import importlib.util                                                    # noqa: E402

_s = importlib.util.spec_from_file_location(
    'cave_dis', os.path.join(L.ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(L.OUTDIR, exist_ok=True)
os.makedirs(L.AUD, exist_ok=True)

DRAWSTRING_LO, DRAWSTRING_HI = 0x219A70, 0x219E00
ICON_IMMS = (0xFFB1, 0xFFB5)
SAFE_IMM = 0xFF00          # addiu rX,zero,0xFF00 ⇒ rX = 0xFFFFFF00 = −256 ⇒ 永不等于符号扩展字节


# ═══════════════════════ 原盘 ELF 的哨兵特判站点（全量扫描）═══════════════════════
def find_icon_imm_sites(elf_path=L.ORIG_ELF):
    """扫全 .text，找 `addiu rX,zero,0xFFB1|0xFFB5`。返回 [{va, word, rt, in_drawstring}]。"""
    elf = CD.Elf(elf_path)
    va0, _off, fsz = elf.text()
    out = []
    for va in range(va0, va0 + fsz - 4, 4):
        w = elf.word(va)
        if (w >> 26) == 0x09 and ((w >> 21) & 0x1F) == 0 and (w & 0xFFFF) in ICON_IMMS:
            out.append(dict(va=va, word=w, rt=(w >> 16) & 0x1F,
                            in_drawstring=(DRAWSTRING_LO <= va < DRAWSTRING_HI)))
    return out


# ═══════════════════════ 宽度模型（用于选搬移目标）═══════════════════════
def width_tables():
    """从**原盘** MENU FONT.RES 读 3 个面的记录表 ⇒ {face: {byte: width}}。

    CharWidth（VA 0x21AD10）原义：
      · font+0x24 != 0  ⇒ 直接返回 font+0x0C（固定宽度，与字节无关）
      · c == 0x20       ⇒ 返回 font+0x14（空格宽）
      · c ∈ {0xB1,0xB5} ⇒ **硬编码返回 20**（0x21AD38 / 0x21AD4C）
      · 否则 idx = (c − face->firstchar) & 0xFF；idx<0 或 idx>=nrec ⇒ 0；宽 = rec[idx].b1
    这里按 face->firstchar = 0x20 计算（HUGE 报告 §A.9 的 32=0x20）。只用于**选点**，不做结论。
    """
    iso = T.Iso(L.EN_ISO)
    e = iso.img_entry(T.MENU_LBA, 4)
    blob = b''.join(s[0] for s in T.lzo_subs(iso.read(e['iso_off'], e['stored'])))
    iso.close()
    _end, faces = T.parse_ft_faces(blob)
    tabs = {}
    for (nm, _fld, recs) in faces:
        firstchar, nrec = 0x20, len(recs)
        w = {}
        for b in range(L.LEAD_LO, L.TRAIL_HI + 1):
            if b in L.SENTINELS:
                w[b] = 20                                  # ★ 硬编码
                continue
            idx = (b - firstchar) & 0xFF
            w[b] = 0 if idx >= nrec else recs[idx][1]
        tabs[nm] = w
    return tabs


def choose_pairs(sent_pairs, used, tabs):
    """给每个哨兵对偶码 (L,T) 选**互不相同**的「空闲且两字节都非哨兵」新对偶码。

    · 候选 = 全空间里 (L',T') 使 (L',T') ∉ used、L' ∉ 哨兵、T' ∉ 哨兵
    · 代价 = Σ_faces (|W(新 lead)−W(原 lead)| + |W(新 trail)−W(原 trail)|)（布局扰动最小）
    · 用**贪心匹配**保证单射：每轮取「当前未分配源 × 未占用目标」里代价最小的那一对。
    """
    free = [(l, t) for l in range(L.LEAD_LO, L.PRESENT_LEAD_HI)
            for t in range(L.TRAIL_LO, L.TRAIL_HI + 1)
            if (l, t) not in used and l not in L.SENTINELS and t not in L.SENTINELS]

    def cost(src, dst):
        l, t = src
        l2, t2 = dst
        return sum(abs(tabs[f][l2] - tabs[f][l]) + abs(tabs[f][t2] - tabs[f][t])
                   for f in tabs)

    todo = sorted(sent_pairs)
    avail = set(free)
    plan = {}
    while todo:
        best = None
        for src in todo:
            for dst in avail:
                c = cost(src, dst)
                if best is None or (c, dst, src) < best[0]:
                    best = ((c, dst, src), src, dst)
        (c, _d, _s), src, dst = best
        plan[src] = dict(new=dst, cost=c,
                         dw={f: [tabs[f][dst[0]] - tabs[f][src[0]],
                                 tabs[f][dst[1]] - tabs[f][src[1]]] for f in tabs})
        todo.remove(src)
        avail.discard(dst)
    return plan, free


# ═══════════════════════ 构建 ═══════════════════════
def build(name, plan_fn, why, do_write=True):
    print('=' * 78)
    print('[build] %s\n        基底 = %s\n        理由 = %s'
          % (name, os.path.relpath(L.BASE_CVAR, L.ROOT), why))
    cs = T.Charset()
    conts = L.load_all(L.BASE_CVAR)
    _bm, _bg = conts['EN_STRINGS.RES@MENU']['blob'], conts['EN_STRINGS.RES@GR']['blob']
    _n = min(len(_bm), len(_bg))
    n_diff_mg = sum(1 for k in range(_n) if _bm[k] != _bg[k])
    print('   [口径] 两个 LANG 容器 blob 长度 %d/%d（GR 比 MENU 多 %d B）；'
          '公共前缀内逐字节不同 %d 处'
          % (len(_bm), len(_bg), len(_bg) - len(_bm), n_diff_mg))

    used, sent_pairs, per_tag_sites = set(), set(), {}
    for tag, c in conts.items():
        sites = []
        for (g, i, ln, data) in L.entries_of(c):
            trail, _bare, pairs = L.scan_payload(data)
            used |= pairs
            for (off, lead, t) in trail:
                sent_pairs.add((lead, t))
                sites.append(dict(key=('G%02d.I%03d' % (g + 1, i)) if g is not None else 'NODE%04d' % i,
                                  g=g, i=i, off=off, lead=lead, trail=t,
                                  char=cs.pair_of.get((lead, t))))
        per_tag_sites[tag] = sites
    tabs = width_tables()
    pair_plan, free = choose_pairs(sent_pairs, used, tabs)
    alias = {k: tuple(v['new']) for k, v in pair_plan.items()}
    assert len(set(alias.values())) == len(alias), '替代表不是单射！'
    print('   哨兵对偶码 %d 个（载荷位置 LANG=%d XML=%d）；空闲候选 %d；替代表单射 ✓'
          % (len(sent_pairs), len(per_tag_sites['EN_STRINGS.RES@MENU']),
             len(per_tag_sites['EN_SPECIAL_FEATURE.XML']), len(free)))
    tot_dw = {f: 0 for f in tabs}
    for k in sorted(pair_plan):
        v = pair_plan[k]
        for f in tabs:
            tot_dw[f] += abs(v['dw'][f][0]) + abs(v['dw'][f][1])
        print('      %02X%02X %-2s -> %02X%02X %-2s  ΔW=%s'
              % (k[0], k[1], cs.pair_of.get(k), v['new'][0], v['new'][1],
                 cs.pair_of.get(v['new']), v['dw']))
    print('   Σ|ΔW| 每面：%s' % tot_dw)

    target = plan_fn()
    slots, report = [], {'containers': {}, 'elf_patch': None, 'alias': {}, 'site_list': {}}
    report['alias'] = {'%02X%02X' % k: dict(new='%02X%02X' % v['new'],
                                            char=cs.pair_of.get(k),
                                            new_char=cs.pair_of.get(tuple(v['new'])),
                                            cost=v['cost'], dw=v['dw'])
                       for k, v in sorted(pair_plan.items())}
    report['width_model'] = dict(faces={f: len(tabs[f]) for f in tabs}, sum_abs_dw=tot_dw,
                                 note='W(0xB1)=W(0xB5)=20 是原盘 CharWidth 的硬编码；其余为 '
                                      'rec[(byte−0x20)].b1')
    dec_stats = {}
    for tag, c in sorted(conts.items()):
        is_xml = (c['kind'] != 'LANG')
        do = target['XML'] if is_xml else target['LANG']
        old_ents = L.entries_of(c)
        if not do:
            slots.append((c['entry']['iso_off'], c['raw']))
            report['containers'][tag] = dict(mode='keep_slot', n_sites_left=len(per_tag_sites[tag]),
                                             note='本盘不动此槽；盘上原有哨兵 trail %d 处'
                                                  % len(per_tag_sites[tag]))
            print('   %-26s keep（不动；原哨兵 %d 处）' % (tag, len(per_tag_sites[tag])))
            continue
        if is_xml:
            nb, hits, _info = L.apply_xml(c['blob'], alias)
        else:
            nb, hits, _info = L.apply_lang(c['blob'], alias)
        assert len(nb) == len(c['blob'])
        new_ents = L.entries_of(dict(c, blob=nb))
        assert len(new_ents) == len(old_ents)
        assert all(a[2] == b[2] for a, b in zip(old_ents, new_ents)), '条目长度被改坏'
        if not is_xml:
            e1, _u1 = T.parse_lang(c['blob'])
            e2, _u2 = T.parse_lang(nb)
            assert len(e1) == len(e2) and all((a.g, a.i, a.length) == (b.g, b.i, b.length)
                                              for a, b in zip(e1, e2)), '条目 1:1 被破坏'
        # ★ 解码等价（替代表口径）
        n_bad, ex = 0, []
        for (a, b) in zip(old_ents, new_ents):
            t0, _m0 = cs.decode(a[3])
            t1, _m1 = L.decode_with_alias(b[3], cs, alias)
            if t0 != t1:
                n_bad += 1
                if len(ex) < 5:
                    ex.append(dict(key='%s#%d' % (tag, a[1]), old=t0[:80], new=t1[:80]))
        n_raw = sum(1 for (a, b) in zip(old_ents, new_ents)
                    if cs.decode(a[3])[0] != cs.decode(b[3])[0])
        dec_stats[tag] = dict(n_entries=len(old_ents), n_sites=len(hits),
                              decode_alias_mismatch=n_bad,
                              decode_without_alias_mismatch_entries=n_raw,
                              examples=ex)
        print('   %-26s repack  改 %d 处；条目 %d（长度全同）｜替代表解码不符 %d 条；'
              '未用替代表时不同 %d 条' % (tag, len(hits), len(new_ents), n_bad, n_raw))
        frame, n_rep = L.TB.repack(c, nb, tag)
        assert len(frame) <= c['entry']['stored'], '%s 帧 %d > 槽 %d' % (tag, len(frame), c['entry']['stored'])
        new_raw = frame + b'\x00' * (c['entry']['stored'] - len(frame))
        slots.append((c['entry']['iso_off'], new_raw))
        rep = dict(mode='repack', frame_len=len(frame), resub=n_rep,
                   iso_off=c['entry']['iso_off'], stored=c['entry']['stored'],
                   real=c['entry']['real'], slot_changed=(new_raw != c['raw']))
        rep.update(dec_stats[tag])
        report['containers'][tag] = rep
        report['site_list'][tag] = [dict(s, new='%02X%02X' % alias[(s['lead'], s['trail'])])
                                    for s in hits]
    report['decode_stats'] = dec_stats

    # ── ELF 补丁（SENT_02）──
    sites = find_icon_imm_sites()
    report['elf_icon_imm_sites_all'] = [
        dict(va='0x%X' % s['va'], imm='0x%04X' % (s['word'] & 0xFFFF),
             in_drawstring=s['in_drawstring']) for s in sites]
    if target.get('ELF'):
        ds = [s for s in sites if s['in_drawstring']]
        assert len(ds) == 8, 'DrawString 里的图标立即数站点数 = %d（预期 8）' % len(ds)
        report['elf_patch'] = dict(
            n=len(ds), safe_imm='0x%04X' % SAFE_IMM,
            sites=[dict(va='0x%X' % s['va'], iso_off=L.iso_off_of_va(s['va']),
                        old_word='0x%08X' % s['word'],
                        new_word='0x%08X' % ((s['word'] & 0xFFFF0000) | SAFE_IMM),
                        old_imm='0x%04X' % (s['word'] & 0xFFFF), new_imm='0x%04X' % SAFE_IMM,
                        rt=s['rt']) for s in ds],
            note='DrawString 区间 [0x%X,0x%X)；`addiu rX,zero,imm` 的立即数 → 0xFF00（= −256，'
                 '任何符号扩展字节都不可能等于它）' % (DRAWSTRING_LO, DRAWSTRING_HI))
    else:
        report['elf_patch'] = dict(n=0, note='本盘不动 ELF')

    out_iso = os.path.join(L.OUTDIR, name + '.iso')
    if not do_write:
        print('   [dry] 未写盘。产物应为 %s' % out_iso)
        return report

    if os.path.exists(out_iso):
        os.remove(out_iso)
    shutil.copyfile(L.BASE_CVAR, out_iso)
    with open(out_iso, 'r+b') as f:
        for (off, data) in slots:
            f.seek(off)
            f.write(data)
        for p in (report['elf_patch']['sites'] if target.get('ELF') else []):
            f.seek(p['iso_off'])
            f.write(struct.pack('<I', int(p['new_word'], 16)))
        f.flush()
        os.fsync(f.fileno())

    # ── 回读自检 ──
    chk = T.Iso(out_iso)
    leftover = {}
    for tag, c in conts.items():
        e2 = chk.img_entry(c['lba'], c['idx'])
        assert (e2['stored'], e2['real'], e2['off'], e2['name']) == \
               (c['entry']['stored'], c['entry']['real'], c['entry']['off'], c['entry']['name']), \
            '%s 条目字段被改坏' % tag
        raw2 = bytes(chk.read(e2['iso_off'], e2['stored']))
        blob2 = b''.join(s[0] for s in T.lzo_subs(raw2))
        if report['containers'][tag]['mode'] == 'keep_slot':
            assert raw2 == c['raw'], '%s keep 模式应逐字节不变' % tag
            report['containers'][tag]['readback'] = '槽 %d B 逐字节未变' % len(raw2)
        else:
            assert len(blob2) == len(c['blob'])
            e_new = L.entries_of(dict(c, blob=blob2))
            e_old = L.entries_of(c)
            assert all(a[2] == b[2] for a, b in zip(e_old, e_new)), '回读条目长度不符'
            nb_bad = sum(1 for (a, b) in zip(e_old, e_new)
                         if cs.decode(a[3])[0] != L.decode_with_alias(b[3], cs, alias)[0])
            assert nb_bad == 0, '回读解码等价失败 %d 条' % nb_bad
            report['containers'][tag]['readback'] = \
                'blob %d B, 条目 %d, 替代表解码等价 ✓' % (len(blob2), len(e_new))
        leftover[tag] = sum(len(L.scan_payload(d)[0]) for (_g, _i, _l, d) in
                            L.entries_of(dict(c, blob=blob2)))
    for p in (report['elf_patch']['sites'] if target.get('ELF') else []):
        got = struct.unpack('<I', bytes(chk.read(p['iso_off'], 4)))[0]
        assert got == int(p['new_word'], 16), 'ELF 补丁回读不符 @0x%X' % p['iso_off']
        report['elf_patch']['readback'] = '%d 处逐字回读与声明一致 ✓' % report['elf_patch']['n']
    chk.close()
    report['leftover_trail_sentinels_after_patch'] = leftover
    report['sentinels_removed'] = {
        tag: len(per_tag_sites[tag]) - leftover[tag] for tag in conts}

    runs = L.diff_byte_runs(L.BASE_CVAR, out_iso)
    total = sum(n for _o, n in runs)
    allowed = [(c['entry']['iso_off'], c['entry']['stored'], tag)
               for tag, c in conts.items() if report['containers'][tag]['mode'] != 'keep_slot']
    for p in (report['elf_patch']['sites'] if target.get('ELF') else []):
        allowed.append((p['iso_off'], 4, 'ELF@%s' % p['va']))
    outside = [(o, n) for (o, n) in runs
               if not any(a <= o and o + n <= a + ln for (a, ln, _t) in allowed)]
    report.update(name=name, base=os.path.relpath(L.BASE_CVAR, L.ROOT), why=why,
                  out=os.path.relpath(out_iso, L.ROOT), size=os.path.getsize(out_iso),
                  sha256=L.sha256_file(out_iso), diff_runs=len(runs), diff_bytes=total,
                  diff_runs_outside_allowed=len(outside), diff_runs_outside_list=outside,
                  diff_runs_list=[[o, n] for (o, n) in runs],
                  build_cmd='python work\\builds\\GR_SENT\\tools\\sent_build.py %s' % name,
                  target=target,
                  selfcheck=dict(size_eq_base=(os.path.getsize(out_iso) ==
                                               os.path.getsize(L.BASE_CVAR)),
                                 allowed_region_only=(len(outside) == 0)))
    print('   [out] %s\n         sha256=%s  %d B  diff %d run / %d B  允许区外 %d run'
          % (report['out'], report['sha256'], report['size'],
             report['diff_runs'], report['diff_bytes'], len(outside)))
    print('         产物盘剩余哨兵 trail：%s ｜已移除：%s' % (leftover, report['sentinels_removed']))
    L.write_json(os.path.join(L.OUTDIR, name + '.meta.json'), report)
    return report


PLANS = {
    'SENT_01_trail_fix': (lambda: dict(LANG=True, XML=True, ELF=False),
                          '候选 R 的正向对照：把 3 个容器里所有「对偶码 trail = 0xB1/0xB5」'
                          '的字整对搬到安全空闲对偶码 ⇒ 盘上不再有「汉字第二字节 = 图标哨兵」'
                          '这一形态（LANG 286 处 + XML 158 处）；其余一字不动。'),
    'SENT_02_icon_path_off': (lambda: dict(LANG=False, XML=False, ELF=True),
                              '候选 R 的反向对照（改动最小）：只把原盘 DrawString 里对 '
                              '0xB1/0xB5 的 7 处图标特判立即数改成永不命中 ⇒ 等价于「关掉图标'
                              '路径」；文本/图集/结构一字不动。'),
    'SENT_03_xml_only': (lambda: dict(LANG=False, XML=True, ELF=False),
                         '只搬移 EN_SPECIAL_FEATURE.XML 的 158 处哨兵（LANG 原样保留）'
                         '⇒ 与 SENT_04 构成 {LANG,XML}×{改,不改} 的 2×2 闭合。'),
    'SENT_04_lang_only': (lambda: dict(LANG=True, XML=False, ELF=False),
                          '只搬移两个 LANG 容器的 286 处哨兵（XML 原样保留）'
                          '⇒ 与 SENT_03 构成 2×2 闭合。'),
}


def main():
    want = sys.argv[1:] or list(PLANS)
    dry = os.environ.get('SENT_DRY') == '1'
    summ = {}
    for nm in want:
        fn, why = PLANS[nm]
        rep = build(nm, fn, why, do_write=not dry)
        summ[nm] = dict(sha256=rep.get('sha256'), size=rep.get('size'),
                        diff_runs=rep.get('diff_runs'), diff_bytes=rep.get('diff_bytes'),
                        out=rep.get('out'), base=rep.get('base'),
                        leftover=rep.get('leftover_trail_sentinels_after_patch'),
                        removed=rep.get('sentinels_removed'))
    if not dry:
        sp = os.path.join(L.OUTDIR, 'summary.json')
        if os.path.exists(sp):                      # 支持分批重建：并入既有 summary
            try:
                old = json.load(open(sp, encoding='utf-8'))
                old.update(summ)
                summ = old
            except Exception:                       # noqa: BLE001
                pass
        L.write_json(sp, summ)
        print()
        for k, v in summ.items():
            print('%-24s %s  diff %s run / %s B  剩余 %s' % (k, v['sha256'], v['diff_runs'],
                                                            v['diff_bytes'], v['leftover']))


if __name__ == '__main__':
    main()
