# -*- coding: utf-8 -*-
r"""txt_build.py —— 任务 C：造决定性验证盘（写 work\builds\GR_TXT\）。

三张盘（每张都是**单变量**：相对基底只改 3 个文本容器的槽内容，其它一字不动）：

  TXT_01_short.iso      基底 = CVAR_04_text.iso（= 已实证会崩的最小复现盘）
                        改动 = 两个 LANG 容器里**所有 zh_len > en_len 的条目**截短到
                               zh_len ≤ en_len（A 审计里 45+45 = 90 条）
  TXT_03_len_eq_en.iso  基底 = CVAR_04_text.iso
                        改动 = 两个 LANG 容器里**全部 2,232 条**载荷用空格补齐/截短到
                               **恰好等于英文原串字节长度**（总量 = 英文原盘）
  TXT_02_orig_text.iso  基底 = GR_ZH113b.iso
                        改动 = 3 个容器的槽内容**整体换成英文原盘的同名槽**（逐字节）
                               ⇒ "其余全汉化、文本是英文" ⇒ 与 CVAR_05_elf_atlas.iso 互镜像

安全约束（每条都断言）：
  · IMG 条目表的 stored / real / off / name 一个字节都不改（本盘上 EN 与 ZH 这三个容器的
    stored/real 本来就相同，实测见 audit/A_len_audit.json containers 段）
  · 解压总长不变（LANG 用 `repack` 的既有口径：未变子流照搬原压缩字节，变了的重压并回环自检）
  · 帧长 ≤ 槽长 stored；槽内帧后余量按既有约定补 0（与 GR_ZH113b 实测一致：tail 非零 = 0）
  · 除这 3 个槽以外，产物与基底逐字节相同（用 1MB→4KB→字节 三段式 diff 证明）

只读：基底 ISO 一律 mmap(ACCESS_READ)；EN 基线只读。
"""
import hashlib
import json
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
OUTDIR = os.path.join(ROOT, 'work', 'builds', 'GR_TXT')
sys.path.insert(0, os.path.join(ROOT, 'tools', 'text_csv'))
import tcslib as T                                                       # noqa: E402

EN_ISO = os.path.join(ROOT, r"third_party\orig\ps2\Tom Clancy's Ghost Recon (USA).iso")
BASE_CVAR = os.path.join(ROOT, r"work\builds\GR_CVAR\CVAR_04_text.iso")
BASE_ZH = os.path.join(ROOT, r"work\builds\GR_ZH113b\GR_ZH113b.iso")
CONTS = ((T.MENU_LBA, 25, 'LANG', 'EN_STRINGS.RES@MENU'),
         (T.GR_LBA, 902, 'LANG', 'EN_STRINGS.RES@GR'),
         (T.MENU_LBA, 283, 'SFXML', 'EN_SPECIAL_FEATURE.XML'))


# ───────────────────────── 读 ─────────────────────────
def load_cont(iso, lba, idx):
    e = iso.img_entry(lba, idx)
    raw = bytes(iso.read(e['iso_off'], e['stored']))
    subs = T.lzo_subs(raw)
    sizes = [s[2] for s in subs]
    raws = [raw[s[3]:s[3] + 8 + s[1]] for s in subs]
    return dict(entry=e, raw=raw, subs=subs, sizes=sizes, raws=raws,
                blob=b''.join(s[0] for s in subs),
                frame_len=sum(8 + s[1] for s in subs), lba=lba, idx=idx)


def lang_walk(blob):
    """按 tcslib.parse_lang 的口径走一遍，返回 (段列表, 尾部起点)。

    段 = ('hdr', bytes) | ('entry', g, i, ln, data, attr) | ('tail', bytes)
    """
    segs = []
    ng, = struct.unpack_from('<I', blob, 0)
    segs.append(('hdr', blob[0:4]))
    p = 4
    for g in range(ng):
        if g:
            segs.append(('hdr', blob[p:p + 4]))
            p += 4
        cnt, = struct.unpack_from('<I', blob, p)
        segs.append(('hdr', blob[p:p + 4]))
        p += 4
        for i in range(cnt):
            ln, = struct.unpack_from('<I', blob, p)
            p += 4
            data = blob[p:p + ln]
            p += ln
            attr = blob[p:p + 2]
            p += 2
            segs.append(('entry', g, i, ln, data, attr))
    return segs, p


def rebuild_lang(blob, fn):
    """fn(g, i, data) -> newdata。结构字节 / attr 一律原样保留；尾部按**零填充**重建
    （原尾部必须已经是全零，否则报错 —— 不许把非零尾料吃掉）。"""
    segs, tail_off = lang_walk(blob)
    tail = blob[tail_off:]
    assert all(b == 0 for b in tail), \
        '尾部 %d B 不是全零 ⇒ 拒绝按零重建' % len(tail)
    out = bytearray()
    n_edit = 0
    for s in segs:
        if s[0] == 'hdr':
            out += s[1]
        elif s[0] == 'entry':
            _k, g, i, ln, data, attr = s
            nd = fn(g, i, data)
            if nd != data:
                n_edit += 1
            out += struct.pack('<I', len(nd)) + nd + attr
        else:                                                        # pragma: no cover
            raise AssertionError(s[0])
    struct_len = len(out)
    assert struct_len <= len(blob), \
        '重建后结构 %d > blob %d —— 装不下（不许截断）' % (struct_len, len(blob))
    out += b'\x00' * (len(blob) - struct_len)
    return bytes(out), n_edit, struct_len


# ───────────────────────── 写 ─────────────────────────
def repack(cont, new_blob, tag):
    """与 work\tools\migrate_legacy.py:repack 同一口径。返回 (frame, n_rep)。"""
    assert len(new_blob) == len(cont['blob']), '解压总长必须不变'
    frame, q, n_rep = bytearray(), 0, 0
    for k, S in enumerate(cont['sizes']):
        part = new_blob[q:q + S]
        q += S
        if part == cont['subs'][k][0]:
            frame += cont['raws'][k]
            continue
        cc = T.lzo_compress(part, level=7, use_m1=True, use_m4=True)
        back, err, _ = T.lzo1x_decompress(cc, out_size=S)
        assert err is None and back == part, '%s 子流 %d 回环失败' % (tag, k)
        frame += struct.pack('<II', len(cc), S) + cc
        n_rep += 1
    assert q == len(new_blob)
    return bytes(frame), n_rep


def diff_runs(a_path, b_path, chunk=1 << 22, win=1 << 12):
    """1MB → 4KB → 字节 三段式精确差异 run 列表 [(off,len)]，只读。"""
    runs = []
    with open(a_path, 'rb') as fa, open(b_path, 'rb') as fb:
        base = 0
        while True:
            ba = fa.read(chunk)
            bb = fb.read(chunk)
            if not ba:
                break
            assert len(ba) == len(bb)
            if ba == bb:
                base += len(ba)
                continue
            for o in range(0, len(ba), win):
                sa = ba[o:o + win]
                sb = bb[o:o + win]
                if sa == sb:
                    continue
                for i in range(len(sa)):
                    if sa[i] != sb[i]:
                        p = base + o + i
                        if runs and runs[-1][0] + runs[-1][1] == p:
                            runs[-1][1] += 1
                        else:
                            runs.append([p, 1])
            base += len(ba)
    return [(a, b) for (a, b) in runs]


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


# ───────────────────────── 主 ─────────────────────────
def build(name, base_path, why, plan, do_write=True):
    print('=' * 78)
    print('[build] %s   基底 = %s' % (name, os.path.relpath(base_path, ROOT)))
    print('        理由: %s' % why)
    iso = T.Iso(base_path)
    en = T.Iso(EN_ISO)
    conts, slots, report = [], [], {'containers': {}}
    en_ents = {}
    for (lba, idx, kind, tag) in CONTS:
        c = load_cont(iso, lba, idx)
        ce = load_cont(en, lba, idx)
        c['kind'], c['tag'] = kind, tag
        c['en'] = ce
        if kind == 'LANG':
            ents, used = T.parse_lang(c['blob'])
            eens, _ = T.parse_lang(ce['blob'])
            assert len(ents) == len(eens), (tag, len(ents), len(eens))
            assert all(ents[i].g == eens[i].g and ents[i].i == eens[i].i
                       for i in range(len(ents)))
            en_ents[tag] = eens
        conts.append(c)

    edits = plan(conts, en_ents)
    for c in conts:
        action, new_blob, info = edits[c['tag']](c)
        if action == 'keep':
            new_raw = c['raw']
            checks = dict(mode='keep_slot', n_edit=0)
        elif action == 'copy_en':
            new_raw = c['en']['raw']
            checks = dict(mode='copy_en_slot',
                          en_frame_len=c['en']['frame_len'], n_edit=0)
        else:
            assert action == 'repack'
            frame, n_rep = repack(c, new_blob, c['tag'])
            assert len(frame) <= c['entry']['stored'], \
                '%s 帧 %d > 槽 %d' % (c['tag'], len(frame), c['entry']['stored'])
            new_raw = frame + b'\x00' * (c['entry']['stored'] - len(frame))
            checks = dict(mode='repack', frame_len=len(frame), resub=n_rep)
        assert len(new_raw) == c['entry']['stored']
        checks.update(info)
        checks.update(iso_off=c['entry']['iso_off'], stored=c['entry']['stored'],
                      real=c['entry']['real'],
                      slot_changed=(new_raw != c['raw']))
        slots.append((c['entry']['iso_off'], new_raw))
        report['containers'][c['tag']] = checks
        print('   %-24s %s  %s' % (c['tag'], checks['mode'],
                                   {k: v for k, v in checks.items()
                                    if k not in ('mode', 'iso_off', 'stored', 'real')}))
    iso.close()
    en.close()

    out_iso = os.path.join(OUTDIR, name + '.iso')
    if not do_write:
        print('   [dry] 不写盘。产物本应为 %s' % out_iso)
        return report
    if os.path.exists(out_iso):
        os.remove(out_iso)
    shutil.copyfile(base_path, out_iso)
    with open(out_iso, 'r+b') as f:
        for (off, data) in slots:
            f.seek(off)
            f.write(data)
        f.flush()
        os.fsync(f.fileno())

    # ── 自检 ──
    chk = T.Iso(out_iso)
    for c in conts:
        e2 = chk.img_entry(c['lba'], c['idx'])
        assert (e2['stored'], e2['real'], e2['off']) == \
               (c['entry']['stored'], c['entry']['real'], c['entry']['off']), \
            '%s 条目字段被改坏' % c['tag']
        raw2 = bytes(chk.read(e2['iso_off'], e2['stored']))
        blob2 = b''.join(s[0] for s in T.lzo_subs(raw2))
        rep = report['containers'][c['tag']]
        if rep['mode'] == 'copy_en_slot':
            assert blob2 == c['en']['blob'], '%s 回读 != 英文原盘 blob' % c['tag']
            rep['readback'] = 'blob == EN 原盘 (%d B)' % len(blob2)
        elif rep['mode'] == 'keep_slot':
            assert raw2 == c['raw'], '%s keep 模式槽内容应逐字节不变' % c['tag']
            rep['readback'] = '槽 %d B 逐字节未变' % len(raw2)
        else:
            rep['readback'] = 'blob %d B, n_entries=%d' % (
                len(blob2), len(T.parse_lang(blob2)[0]) if c['kind'] == 'LANG' else -1)
        assert e2['name'] == c['entry']['name']
    chk.close()

    runs = diff_runs(base_path, out_iso)
    total = sum(n for _o, n in runs)
    outside = [r for r in runs
               if not any(off <= r[0] and r[0] + r[1] <= off + stored
                          for (off, stored) in
                          [(c['entry']['iso_off'], c['entry']['stored']) for c in conts])]
    report.update(name=name, base=os.path.relpath(base_path, ROOT),
                  why=why, out=os.path.relpath(out_iso, ROOT),
                  size=os.path.getsize(out_iso), sha256=sha256_file(out_iso),
                  diff_runs=len(runs), diff_bytes=total,
                  diff_runs_outside_slots=len(outside),
                  n_slots_changed=sum(1 for (c, s) in zip(conts, slots)
                                      if s[1] != c['raw']),
                  diff_runs_list=[[o, n] for (o, n) in runs[:400]],
                  diff_runs_truncated=len(runs) > 400,
                  build_cmd='python work\\builds\\GR_TXT\\tools\\txt_build.py %s' % name,
                  selfcheck=dict(slot_only=(len(outside) == 0),
                                 size_eq_base=(os.path.getsize(out_iso) ==
                                               os.path.getsize(base_path))))
    with open(os.path.join(OUTDIR, name + '.meta.json'), 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print('   [out] %s  sha256=%s  %d B  diff %d run / %d B  槽外 %d run'
          % (report['out'], report['sha256'][:16], report['size'],
             report['diff_runs'], report['diff_bytes'], len(outside)))
    return report


# ───────────────────────── 三个盘的编辑方案 ─────────────────────────
def plan_txt01(conts, en_ents):
    """把 zh_len > en_len 的条目截短到 ≤ en_len；XML 一字不动。"""
    def mk(c):
        if c['kind'] != 'LANG':
            return lambda cc: ('keep', None,
                               dict(note='SFXML 无增长条目(A 实测 grew=0) ⇒ 整槽不动'))
        eens = en_ents[c['tag']]
        ents, _ = T.parse_lang(c['blob'])
        stat = dict(n_over=0, n_trim=0, max_over=0)
        elen = {}
        for e in eens:
            elen[(e.g, e.i)] = e.length
        for e in ents:
            L = elen[(e.g, e.i)]
            if e.length > L:
                stat['n_over'] += 1
                stat['max_over'] = max(stat['max_over'], e.length - L)

        def fn2(g, i, data):
            L = elen[(g, i)]
            if len(data) > L:
                stat['n_trim'] += 1
                return data[:L]
            return data
        def runner(cc):
            nb, n_edit, used = rebuild_lang(cc['blob'], fn2)
            stat['n_edit_entries'] = n_edit
            stat['rebuilt_used_end'] = used
            ents2, _u2 = T.parse_lang(nb)
            bad = [k for k, e in enumerate(ents2) if e.length > elen[(e.g, e.i)]]
            stat['n_le_en'] = len(ents2) - len(bad)
            stat['n_gt_en'] = len(bad)
            stat['sum_payload'] = sum(e.length for e in ents2)
            stat['blob_len'] = len(nb)
            return ('repack', nb, stat)
        return runner
    return {c['tag']: mk(c) for c in conts}


def plan_txt03(conts, en_ents):
    """把两个 LANG 容器的全部载荷补/截到恰好 == 英文原串字节长度；XML 一字不动。"""
    def mk(c):
        if c['kind'] != 'LANG':
            return lambda cc: ('keep', None,
                               dict(note='XML 整槽不动（<text> 口径不完整, 不做半吊子单变量）'))
        eens = en_ents[c['tag']]
        elen = {}
        for e in eens:
            elen[(e.g, e.i)] = e.length
        stat = dict(n_pad=0, n_trim=0, n_same=0)

        def fn(g, i, data):
            L = elen[(g, i)]
            if len(data) > L:
                stat['n_trim'] += 1
                return data[:L]
            if len(data) < L:
                stat['n_pad'] += 1
                return data + b' ' * (L - len(data))
            stat['n_same'] += 1
            return data
        def runner(cc):
            nb, n_edit, used = rebuild_lang(cc['blob'], fn)
            stat['n_edit_entries'] = n_edit
            stat['rebuilt_used_end'] = used
            ents2, used2 = T.parse_lang(nb)
            bad = [k for k, e in enumerate(ents2) if e.length != elen[(e.g, e.i)]]
            stat['n_len_eq_en'] = len(ents2) - len(bad)
            stat['n_len_mismatch'] = len(bad)
            stat['sum_payload'] = sum(e.length for e in ents2)
            stat['blob_len'] = len(nb)
            return ('repack', nb, stat)
        return runner
    return {c['tag']: mk(c) for c in conts}


def plan_txt02(conts, en_ents):
    """整槽照搬英文原盘（3 个容器全换）。"""
    return {c['tag']: (lambda cc: ('copy_en', None,
                                   dict(note='槽内容 = 英文原盘逐字节')))
            for c in conts}


PLANS = {
    'TXT_01_short': (BASE_CVAR, plan_txt01,
                     '基底用 CVAR_04_text.iso：它是**已实证会崩**的最小复现盘'
                     '（原盘 ELF + 原盘图集/记录表 + 3 个中文文本容器），'
                     '只改文本一个变量 ⇒ 行为差异可直接解释；'
                     '若换 GR_ZH113b 为基底, 基底本身还有 26,502 B 的 ELF/图集/结构改动, 不是单变量。'),
    'TXT_03_len_eq_en': (BASE_CVAR, plan_txt03,
                         '同 TXT_01 的基底。TXT_01 封顶（≤ 英文长度）、本盘拉到等长（== 英文长度）'
                         '⇒ 两张盘把"长度"这一个变量从两侧夹住。'),
    'TXT_02_orig_text': (BASE_ZH, plan_txt02,
                         '按任务书用 GR_ZH113b.iso：做成"其余全汉化、3 份文本是英文"的盘, '
                         '与 CVAR_05_elf_atlas.iso（ELF+图集、无文本改动）互为镜像。'),
}


def main():
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    want = sys.argv[1:] or list(PLANS)
    if not os.path.isdir(OUTDIR):
        os.makedirs(OUTDIR)
    dry = os.environ.get('TXT_DRY') == '1'
    summ = {}
    for nm in want:
        base, planner, why = PLANS[nm]
        summ[nm] = build(nm, base, why, planner, do_write=not dry)
    if not dry:
        with open(os.path.join(OUTDIR, 'summary.json'), 'w', encoding='utf-8') as f:
            json.dump({k: dict(sha256=v['sha256'], size=v['size'],
                               diff_runs=v['diff_runs'], diff_bytes=v['diff_bytes'],
                               out=v['out'], base=v['base'])
                       for k, v in summ.items()}, f, ensure_ascii=False, indent=1)
        for k, v in summ.items():
            print('%-20s %s  %d B  diff %d run / %d B  槽外 %d'
                  % (k, v['sha256'][:16], v['size'], v['diff_runs'],
                     v['diff_bytes'], v['diff_runs_outside_slots']))


if __name__ == '__main__':
    main()
