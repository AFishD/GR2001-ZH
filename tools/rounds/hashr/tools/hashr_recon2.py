# -*- coding: utf-8 -*-
r"""hashr_recon2.py — 逐字用量普查 (只读)

① K2 / ZH113b: 只统计**合法对偶码**的哨兵 trail 站点 (修正 recon 的假阳性口径)
② ZH113b: 1504 个已登记对偶字的**用量** (7 个容器的载荷 + 全 IMG 原始 2 字节模式粗扫)
③ 找出"零用量"的已登记对偶字 —— 基底盘重排的候选让位者

输出: work/builds/GR_HASHR/audit/recon2.txt
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                       # noqa: E402
import migrate_legacy as ML                                              # noqa: E402
import zx_lib                                                            # noqa: E402

K2 = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'GR_FA2400_K2.iso')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
CS_K2 = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
CS_BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82',
                       'charset_before_r82.json')
SENT = (0xB1, 0xB5)
OUT = []
CORE = ('EN_STRINGS.RES@MENU', 'EN_STRINGS.RES@GR', 'EN_SPECIAL_FEATURE.XML')


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    OUT.append(s)


def load_cs(path):
    j = json.load(io.open(path, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in j['pair_of'].items()}
    pair_dec = {tuple(v): ch for ch, v in j['pair_of'].items()}
    codes = {ch: int(b) for ch, b in j['codes'].items()}
    code_dec = {int(b): ch for ch, b in j['codes'].items()}
    return j, pair_of, pair_dec, codes, code_dec


def walk(pay, gate, pair_dec):
    """产出 (i, b1, b2, ch) —— 只对**合法对偶码**; 其它字节按 1/2 字节步进一并报出。"""
    i, n = 0, len(pay)
    while i < n:
        b = pay[i]
        if T.LEAD_LO <= b < gate:
            t = pay[i + 1] if i + 1 < n else None
            if t is not None and (b, t) in pair_dec:
                yield (i, b, t, pair_dec[(b, t)], 'pair')
                i += 2
                continue
            yield (i, b, t, None, 'odd-lead')
            i += 1
            continue
        yield (i, b, None, None, 'single')
        i += 1


def container_blobs(iso):
    out = []
    for (kind, img, lba, idx, tag, why) in ML.CONTAINER_SPECS:
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        blob = b''.join(s[0] for s in T.lzo_subs(raw))
        c = dict(name=kind, tag=tag, blob=blob, entry=e, lba=lba, idx=idx)
        ranges, used, info = ML.payload_ranges(c)
        c['ranges'] = ranges
        c['used_end'] = used
        out.append(c)
    return out


def sentinel_report(label, iso_path, cs_path, only_core=True):
    j, pair_of, pair_dec, codes, code_dec = load_cs(cs_path)
    iso = T.Iso(iso_path)
    gate = T.read_decode_gate(iso)
    P('=' * 100)
    P('### %s  gate=0x%02X  pair_of=%d codes=%d' % (label, gate, len(pair_of), len(codes)))
    per_code = collections.Counter()
    per_char = collections.Counter()
    bare = collections.Counter()
    odd = collections.Counter()
    for c in container_blobs(iso):
        n_s = n_b = 0
        for (s, e) in c['ranges']:
            pay = c['blob'][s:e]
            for (_i, b1, b2, ch, kind) in walk(pay, gate, pair_dec):
                if kind == 'pair':
                    if b2 in SENT:
                        per_code[(b1, b2)] += 1
                        per_char[ch] += 1
                        if c['tag'] in CORE:
                            n_s += 1
                elif kind == 'odd-lead':
                    odd[(c['tag'], b1)] += 1
                elif b1 in SENT:
                    bare[(c['tag'], b1)] += 1
                    if c['tag'] in CORE:
                        n_b += 1
        P('  %-24s %s 合法对偶哨兵 %d ; 裸哨兵 %d ; 配不出对的 lead %d'
          % (c['tag'], '★CORE' if c['tag'] in CORE else '      ', n_s, n_b,
             sum(v for (t, _b), v in odd.items() if t == c['tag'])))
    core_chars = collections.Counter()
    for c in container_blobs(iso):
        if c['tag'] not in CORE:
            continue
        for (s, e) in c['ranges']:
            for (_i, b1, b2, ch, kind) in walk(c['blob'][s:e], gate, pair_dec):
                if kind == 'pair' and b2 in SENT:
                    core_chars[ch] += 1
    P('  ---- 3 个中文容器: 合法对偶哨兵 trail 汇总 ----')
    P('  站点合计 %d ; 涉及对偶码 %d 个 / 字 %d 个'
      % (sum(core_chars.values()), len(per_code), len(core_chars)))
    for ch, n in core_chars.most_common():
        pb = pair_of[ch]
        P('    %-3s  0x%02X%02X slot=%-5d  %4d 处' % (ch, pb[0], pb[1],
                                                       T.pair_slot(*pb), n))
    allsent = sorted(set(per_code))
    P('  ---- 哨兵对偶码是否都被文本用到 ----')
    ids = sorted(set(pair_of.values()))
    sent_reg = [p for p in ids if p[1] in SENT]
    P('  charset 里 trail ∈ {B1,B5} 的登记对偶码 %d 个 ; 其中 3 容器用到 %d 个'
      % (len(sent_reg), len([p for p in sent_reg if p in per_code])))
    never = [pair_dec[p] for p in sent_reg if p not in per_code]
    P('  3 容器**未用到**的哨兵字 %d 个: %s' % (len(never), ' '.join(never)))
    iso.close()
    return dict(gate=gate, pair_of=pair_of, pair_dec=pair_dec, codes=codes,
                code_dec=code_dec, per_code=per_code, per_char=per_char,
                core_chars=core_chars, sent_reg=sent_reg, never=never)


def usage_base(R):
    """ZH113b: 1504 个已登记对偶字在**全部 7 容器载荷**里的用量 + 全 IMG 粗扫。"""
    iso = T.Iso(BASE)
    cs = R['pair_of']
    pair_dec = R['pair_dec']
    gate = R['gate']
    used = collections.Counter()
    for c in container_blobs(iso):
        for (s, e) in c['ranges']:
            for (_i, b1, b2, ch, kind) in walk(c['blob'][s:e], gate, pair_dec):
                if kind == 'pair':
                    used[ch] += 1
    P('')
    P('  ---- 基底盘: 已登记对偶字在 7 个容器载荷里的用量 ----')
    P('  登记 %d 个 ; 用量 >0 的 %d 个 ; **零用量** %d 个'
      % (len(cs), len([1 for ch in cs if used[ch]]), len([1 for ch in cs if not used[ch]])))
    zero = sorted([ch for ch in cs if not used[ch]],
                  key=lambda ch: T.pair_slot(*cs[ch]))
    P('  零用量字 (按槽序): %s' % ' '.join(zero))
    # ── 全 IMG 原始 2 字节模式粗扫 (排除字库 PAK) ──
    pat = collections.Counter()
    entries = []
    for lba, nm in ((zx_lib.MENU_LBA, 'MENU.IMG'), (zx_lib.GR_LBA, 'GR.IMG')):
        for e in zx_lib.entries(iso, lba):
            entries.append((nm, e))
    P('  IMG 条目总数 = %d' % len(entries))
    for ch in zero:
        pat[ch] = 0
    # 只为零用量字扫 (逐条读原始字节, 用 bytes.find 快扫)
    zero_pats = {bytes(cs[ch]): ch for ch in zero}
    for (nm, e) in entries:
        if e['name'] in ('COMMON.PAK',):
            continue
        data = iso.read(e['iso_off'], e['stored'])
        for pb, ch in zero_pats.items():
            k = data.count(pb)
            if k:
                pat[ch] += k
    clean = [ch for ch in zero if pat[ch] == 0]
    P('  零用量字中, 原始 2 字节模式在 IMG 里**一次都不出现**的 %d 个' % len(clean))
    P('  其中按槽序前 60: %s' % ' '.join(clean[:60]))
    dirty = [(ch, pat[ch]) for ch in zero if pat[ch]]
    P('  零用量但原始模式有命中 (可能是别的编码/字形数据巧合) %d 个: %s'
      % (len(dirty), ' '.join('%s:%d' % (c, n) for c, n in dirty[:40])))
    return used, zero, clean, dirty


if __name__ == '__main__':
    RK = sentinel_report('K2', K2, CS_K2)
    RB = sentinel_report('GR_ZH113b', BASE, CS_BASE)
    usage_base(RB)
    os.makedirs(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit'), exist_ok=True)
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit', 'recon2.txt'),
                 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(OUT) + '\n')
