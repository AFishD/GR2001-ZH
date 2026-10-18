# -*- coding: utf-8 -*-
r"""hashr_recon.py — 哨兵 trail 重排: 地面事实普查 (只读)

用法:
    python work/builds/GR_HASHR/tools/hashr_recon.py > work/builds/GR_HASHR/audit/recon.txt

只读: 两个 ISO / 两个 charset / tools/text_csv/**。不写任何既有文件。
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

K2 = os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2', 'GR_FA2400_K2.iso')
BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
CS_K2 = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
CS_BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r82',
                       'charset_before_r82.json')
SENT = (0xB1, 0xB5)
OUT = []


def P(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    OUT.append(s)


def load_cs(path):
    j = json.load(io.open(path, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in j['pair_of'].items()}      # char -> (b1,b2)
    codes = {ch: int(b) for ch, b in j['codes'].items()}            # char -> byte
    pair_dec = {v: k for k, v in pair_of.items()}
    return j, pair_of, codes, pair_dec


def scan_payload(pay, gate, pair_dec, want_trail=SENT):
    """按本盘闸门走字节流。返回 (哨兵 trail 站点, 裸哨兵单字节, 用到的字计数)."""
    sites, bare, used = [], [], collections.Counter()
    i, n = 0, len(pay)
    while i < n:
        b = pay[i]
        if T.LEAD_LO <= b < gate:
            t = pay[i + 1] if i + 1 < n else None
            if t is not None and (b, t) in pair_dec:
                ch = pair_dec[(b, t)]
                used[ch] += 1
                if t in want_trail:
                    sites.append((i, b, t, ch))
                i += 2
                continue
            # 前导但配不出对偶码: 按旧口径吞 2 字节 (登记为异常)
            sites.append((i, b, t, None))
            i += 2 if t is not None else 1
            continue
        if b in want_trail:
            bare.append((i, b))
        else:
            used[chr(b) if b < 0x80 else None] += 0
        i += 1
    return sites, bare, used


def containers(iso):
    out = []
    for (kind, img, lba, idx, tag, why) in ML.CONTAINER_SPECS:
        e = iso.img_entry(lba, idx)
        raw = iso.read(e['iso_off'], e['stored'])
        subs = T.lzo_subs(raw)
        blob = b''.join(s[0] for s in subs)
        c = dict(name=kind, tag=tag, img=img, idx=idx, entry=e, blob=blob, raw=raw, subs=subs)
        ranges, used, info = ML.payload_ranges(c)
        c['ranges'] = ranges
        c['used_end'] = used
        c['info'] = info
        out.append(c)
    return out


def report_disc(label, iso_path, cs_path):
    P('=' * 100)
    P('### %s   %s' % (label, iso_path))
    j, pair_of, codes, pair_dec = load_cs(cs_path)
    P('  charset %s' % cs_path)
    P('  pair_of=%d codes=%d' % (len(pair_of), len(codes)))
    iso = T.Iso(iso_path)
    gate = T.read_decode_gate(iso)
    P('  ELF 解码闸门 = 0x%02X  ⇒ lead ∈ [0x%02X, 0x%02X) 对偶空间 %d'
      % (gate, T.LEAD_LO, gate, (gate - T.LEAD_LO) * 94))
    cs = T.Charset(cs_path)
    # ── 哨兵 trail 站点 ──
    all_sites = []
    P('  %-26s %8s %8s %8s %8s %8s' % ('容器', 'payload', 'trail站', '裸B1/B5', '条目', '区间'))
    for c in containers(iso):
        tot_s, tot_b, used = 0, 0, collections.Counter()
        persite = []
        for (s, e) in c['ranges']:
            ss, bb, u = scan_payload(c['blob'][s:e], gate, pair_dec)
            tot_s += len(ss)
            tot_b += len(bb)
            used.update(u)
            persite.extend([(s + o, b1, b2, ch) for (o, b1, b2, ch) in ss])
        P('  %-26s %8d %8d %8d %8d %8d'
          % (c['tag'], sum(e - s for (s, e) in c['ranges']), tot_s, tot_b,
             c['info'].get('lang_entries', c['info'].get('xml_text')), len(c['ranges'])))
        all_sites.append((c['tag'], persite))
        c['sent_sites'] = persite
    per_char = collections.Counter()
    for (_t, lst) in all_sites:
        for (_o, b1, b2, ch) in lst:
            per_char[(b1, b2, ch)] += 1
    P('  ---- 哨兵 trail 汇总 ----')
    P('  3 容器哨兵 trail 站点合计 = %d ; 涉及对偶码 %d 个 / 字 %d 个'
      % (sum(v for v in per_char.values()), len(per_char),
         len(set(k[2] for k in per_char))))
    for (b1, b2, ch), n in sorted(per_char.items(), key=lambda kv: (-kv[1], kv[0])):
        P('    0x%02X%02X slot=%-5d %-3s  %4d 处  %s'
          % (b1, b2, (b1 - 0xA1) * 94 + (b2 - 0xA1), ch if ch else '??', n,
             ('├ 未登记字' if ch is None else '')))
    # ── 全对偶码占用普查 ──
    cap = (gate - T.LEAD_LO) * 94
    occupied = {T.pair_slot(b1, b2) for (b1, b2) in pair_dec}
    sent_slots = sorted((L - 0xA1) * 94 + (t - 0xA1)
                        for L in range(T.LEAD_LO, gate) for t in SENT)
    P('  ---- 对偶空间 ----')
    P('  gate 容量 %d 槽 ; charset 登记 %d 槽 ; 空闲 %d 槽'
      % (cap, len(occupied), cap - len(occupied)))
    P('  哨兵槽 (trail ∈ {B1,B5}) 共 %d 个: %s%s'
      % (len(sent_slots), sent_slots[:14], ' …' if len(sent_slots) > 14 else ''))
    free_slots = [s for s in range(cap) if s not in occupied]
    P('  完全空闲槽 %d 个%s' % (len(free_slots), (': %s%s' % (free_slots[:20],
      ' …' if len(free_slots) > 20 else '')) if free_slots else ''))
    safe_free = [s for s in free_slots if (s % 94) + 0xA1 not in SENT]
    P('  其中「trail 非哨兵」的空闲槽 %d 个' % len(safe_free))
    # ── 保留/占位槽 ──
    ph = [(ch, pp) for ch, pp in pair_of.items() if 0xE000 <= ord(ch) <= 0xF8FF]
    P('  私有区占位字 %d 个 (U+%04X..U+%04X)'
      % (len(ph), min(ord(c) for c, _ in ph) if ph else 0,
         max(ord(c) for c, _ in ph) if ph else 0))
    iso.close()
    return dict(gate=gate, pair_of=pair_of, codes=codes, pair_dec=pair_dec,
                per_char=per_char, free_slots=free_slots, safe_free=safe_free,
                sent_slots=sent_slots, ph=ph)


if __name__ == '__main__':
    R = {}
    R['k2'] = report_disc('K2 (交付 A 的基线)', K2, CS_K2)
    R['base'] = report_disc('GR_ZH113b (交付 B 的基线)', BASE, CS_BASE)
    os.makedirs(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit'), exist_ok=True)
    with io.open(os.path.join(REPO, 'work', 'builds', 'GR_HASHR', 'audit', 'recon.txt'),
                 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(OUT) + '\n')
