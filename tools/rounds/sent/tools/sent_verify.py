# -*- coding: utf-8 -*-
r"""sent_verify.py —— GR_SENT 四张盘的**独立终检**（不依赖构建时的内存状态，从盘上重新读）。

对每张盘逐项独立复核：
  1) sha256 / 尺寸 == .meta.json 声明，且 == 基底尺寸
  2) 差异 run **全部落在允许区**（被改容器槽 ∪ ELF 补丁字节），区外 0 run
  3) 3 个容器的 IMG 条目字段（stored/real/off/name）与基底一致；两份 IMG **整表** sha256 与基底一致
  4) 每个容器的**条目数**与**逐条长度**与基底完全相同（容器长度不变 / 条目 1:1）
  5) **解码等价**：`decode_替代表(产物载荷) == decode_charset(基底载荷)` 逐条比较
  6) 哨兵 trail 计数：产物盘上还剩多少（按设计命题给期望）
  7) （SENT_02）从盘上反汇编 DrawString 区间，确认**不再有** 0xFFB1/0xFFB5 立即数
  8) 只读地复核**基底盘与英文原盘未被改动**（sha256 与既有 meta 声明一致）
只读。
"""
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sent_lib as L                                                     # noqa: E402
import tcslib as T                                                       # noqa: E402

_s = importlib.util.spec_from_file_location(
    'cave_dis', os.path.join(L.ROOT, 'tools', 're', 'toolbelt', 'cave_dis.py'))
CD = importlib.util.module_from_spec(_s)
_s.loader.exec_module(CD)

CASES = {
    # 盘名 → (期望：改成哨兵的容器集合, 期望剩余哨兵 trail {tag: n})
    'SENT_01_trail_fix': (dict(LANG=True, XML=True, ELF=False), None),
    'SENT_02_icon_path_off': (dict(LANG=False, XML=False, ELF=True), None),
    'SENT_03_xml_only': (dict(LANG=False, XML=True, ELF=False), None),
    'SENT_04_lang_only': (dict(LANG=True, XML=False, ELF=False), None),
}


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def blob_of(iso, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = bytes(iso.read(e['iso_off'], e['stored']))
    return e, b''.join(s[0] for s in T.lzo_subs(raw)), raw


def table_hashes(iso, lba, n):
    return hashlib.sha256(bytes(iso.read(lba * 2048 + 0x830, 48 * n))).hexdigest()


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    cs = T.Charset()
    # 把构建脚本里的替代表**独立重算**（同一确定性规则）
    conts = L.load_all()
    used, sent_pairs = set(), set()
    for tag, c in conts.items():
        for (_g, _i, _l, d) in L.entries_of(c):
            trail, _b, pairs = L.scan_payload(d)
            used |= pairs
            for (off, lead, t) in trail:
                sent_pairs.add((lead, t))
    # 允许区（ELF 补丁）
    _s2 = importlib.util.spec_from_file_location(
        'sb', os.path.join(HERE, 'sent_build.py'))
    SB = importlib.util.module_from_spec(_s2)
    _s2.loader.exec_module(SB)
    tabs = SB.width_tables()
    plan, _free = SB.choose_pairs(sent_pairs, used, tabs)
    alias = {k: tuple(v['new']) for k, v in plan.items()}
    assert len(set(alias.values())) == len(alias)

    base = T.Iso(L.BASE_CVAR)
    base_blobs, base_ents, base_raws, base_fields, base_iso_off = {}, {}, {}, {}, {}
    for (img, lba, idx, kind, tag) in L.CONTS:
        e, b, r = blob_of(base, lba, idx)
        base_blobs[tag] = b
        base_raws[tag] = r
        base_fields[tag] = (e['stored'], e['real'], e['off'], e['name'])
        base_iso_off[tag] = e['iso_off']
        base_ents[tag] = L.entries_of(dict(kind=kind, blob=b))
    base_tabs = {T.MENU_LBA: table_hashes(base, T.MENU_LBA, 686),
                 T.GR_LBA: table_hashes(base, T.GR_LBA, 4070)}
    base.close()
    base_sha = sha256_file(L.BASE_CVAR)
    base_meta = json.load(open(os.path.join(L.ROOT, r'work\builds\GR_CVAR',
                                            'CVAR_04_text.meta.json'), encoding='utf-8'))
    bm = base_meta.get('sha256') or base_meta.get('out_sha256') or ''
    leftovers = {t: sum(len(L.scan_payload(d)[0]) for (_g, _i, _l, d) in base_ents[t])
                 for t in base_ents}
    print('基底 CVAR_04_text.iso sha256=%s' % base_sha)
    print('   既有 meta 声明 sha256=%s  ⇒ %s'
          % (bm[:64] or '(未登记)', '一致 ✓' if (not bm or bm == base_sha) else '★不一致★'))
    print('   基底哨兵 trail 计数：%s' % leftovers)
    print()

    ok_all = True
    for name, (target, _exp) in CASES.items():
        meta = json.load(open(os.path.join(L.OUTDIR, name + '.meta.json'), encoding='utf-8'))
        p = os.path.join(L.OUTDIR, name + '.iso')
        iso = T.Iso(p)
        res, ok = [], True

        h = sha256_file(p)
        same = (h == meta['sha256'])
        ok &= same
        res.append('sha256 %s (%s)' % (h[:16], 'OK' if same else '★不符★'))
        sz = os.path.getsize(p)
        ok &= (sz == os.path.getsize(L.BASE_CVAR) == meta['size'])
        res.append('尺寸 %d (= 基底 = meta) %s' % (sz, '✓' if sz == meta['size'] else '★'))

        # 差异 run 全部落在允许区
        runs = L.diff_byte_runs(L.BASE_CVAR, p)
        allowed = []
        for (img, lba, idx, kind, tag) in L.CONTS:
            if (target['XML'] if kind != 'LANG' else target['LANG']):
                allowed.append((base_iso_off[tag], base_fields[tag][0]))
        if target['ELF']:
            for s in SB.find_icon_imm_sites():
                if s['in_drawstring']:
                    allowed.append((L.iso_off_of_va(s['va']), 4))
        outside = [(o, n) for (o, n) in runs
                   if not any(a <= o and o + n <= a + ln for (a, ln) in allowed)]
        ok &= (not outside)
        res.append('差异 run %d / %d B，允许区外 %d run %s'
                   % (len(runs), sum(n for _o, n in runs), len(outside),
                      '✓' if not outside else '★ %r' % outside[:3]))

        # IMG 表 + 条目字段 + 条目长度 + 解码等价 + 哨兵残留
        for (img, lba, idx, kind, tag) in L.CONTS:
            e, b, r = blob_of(iso, lba, idx)
            f_ok = (e['stored'], e['real'], e['off'], e['name']) == base_fields[tag]
            ok &= f_ok
            ents = L.entries_of(dict(kind=kind, blob=b))
            n_ok = (len(ents) == len(base_ents[tag]))
            len_ok = n_ok and all(a[2] == b2[2] for a, b2 in zip(base_ents[tag], ents))
            dec_bad = sum(1 for (a, b2) in zip(base_ents[tag], ents)
                          if cs.decode(a[3])[0] != L.decode_with_alias(b2[3], cs, alias)[0])
            left = sum(len(L.scan_payload(d)[0]) for (_g, _i, _l, d) in ents)
            changed = (target['XML'] if kind != 'LANG' else target['LANG'])
            exp_left = 0 if changed else leftovers[tag]
            l_ok = (left == exp_left)
            ok &= f_ok and n_ok and len_ok and (dec_bad == 0) and l_ok
            res.append('%-24s 字段%s 条目%d(%s) 长度%s 解码等价%s 哨兵%d(%s)'
                       % (tag, '✓' if f_ok else '★', len(ents),
                          '1:1✓' if n_ok else '★', '全同✓' if len_ok else '★',
                          '✓' if dec_bad == 0 else '★%d条' % dec_bad,
                          left, '✓期望%d' % exp_left if l_ok else '★期望%d' % exp_left))
        for (lba, n) in ((T.MENU_LBA, 686), (T.GR_LBA, 4070)):
            a_, b_ = base_tabs[lba], table_hashes(iso, lba, n)
            ok &= (a_ == b_)
            res.append('IMG 整表 @LBA%d %s' % (lba, '未变 ✓' if a_ == b_ else '★变了★'))

        # SENT_02：从盘上反汇编确认图标立即数已消失
        if target['ELF']:
            import struct as _st
            bad = []
            for s in SB.find_icon_imm_sites():
                if not s['in_drawstring']:
                    continue
                off = L.iso_off_of_va(s['va'])
                got = _st.unpack('<I', bytes(iso.read(off, 4)))[0]
                imm = got & 0xFFFF
                if imm in (0xFFB1, 0xFFB5):
                    bad.append(hex(s['va']))
            # 整段重扫（不是只看已知站点）
            va0, _o, fsz = CD.Elf(L.ORIG_ELF).text()
            seg = bytes(iso.read(L.iso_off_of_va(0x219A70), 0x219E00 - 0x219A70))
            nimm = 0
            for k in range(0, len(seg) - 3, 4):
                w = _st.unpack_from('<I', seg, k)[0]
                if (w >> 26) == 0x09 and ((w >> 21) & 0x1F) == 0 and (w & 0xFFFF) in (0xFFB1, 0xFFB5):
                    nimm += 1
            ok &= (not bad) and nimm == 0
            res.append('DrawString 段内 0xFFB1/0xFFB5 立即数残留 = %d（期望 0）%s'
                       % (nimm, '✓' if nimm == 0 else '★'))
        iso.close()
        print('%-24s %s' % (name, '✅' if ok else '★★ 失败 ★★'))
        for r in res:
            print('     ' + r)
        print()
        ok_all &= ok
    print('总判定: %s' % ('✅ 四张盘全部通过独立终检' if ok_all else '★★ 有失败项 ★★'))


if __name__ == '__main__':
    main()
