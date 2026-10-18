# -*- coding: utf-8 -*-
r"""sent_scan.py —— 候选 R 的取证普查（只读）。

产出：
  audit\A_sentinel_scan.txt   人读汇总
  audit\A_sentinel_scan.json  全部读数（含逐处清单）
  audit\A_trail_sites.csv     逐处哨兵 trail（容器/条目/偏移/lead/trail/替换值）
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sent_lib as L                                                     # noqa: E402
import tcslib as T                                                       # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
os.makedirs(L.AUD, exist_ok=True)


def main():
    cs = T.Charset()
    report = dict(charset=dict(n_pair=len(cs.enc_pair), n_single=len(cs.enc_single),
                               lead_lo=T.LEAD_LO, lead_hi=T.LEAD_HI,
                               trail_lo=T.PAIR_TRAIL_LO, trail_hi=T.PAIR_TRAIL_HI,
                               pair_stride=T.PAIR_STRIDE,
                               pair_capacity=T.pair_capacity()))
    # charset 里 trail ∈ 哨兵 的字
    sent_chars = sorted([(hex(v[0]), hex(v[1]), ch)
                         for ch, v in cs.enc_pair.items() if v[1] in L.SENTINELS])
    report['charset']['n_chars_with_sentinel_trail'] = len(sent_chars)
    report['charset']['chars_with_sentinel_trail'] = sent_chars

    conts = L.load_all()
    rows = []
    per_tag = {}
    used_pairs = {}
    fh = open(os.path.join(L.AUD, 'A_trail_sites.csv'), 'w', encoding='utf-8', newline='\n')
    fh.write('tag,kind,entry_key,entry_index,off_in_payload,lead,trail,char,new_trail,new_pair,'
             'new_pair_free,bare_in_entry\n')
    for tag in ('EN_STRINGS.RES@MENU', 'EN_STRINGS.RES@GR', 'EN_SPECIAL_FEATURE.XML'):
        c = conts[tag]
        ents = L.entries_of(c)
        tot = sum(e[2] for e in ents)
        n_b1 = n_b5 = n_ent_with = 0
        n_trail = n_bare = 0
        pair_used = set()
        detail = []
        for (g, i, ln, data) in ents:
            trail, bare, pairs = L.scan_payload(data)
            pair_used |= pairs
            if trail:
                n_ent_with += 1
            n_b1 += data.count(0xB1)
            n_b5 += data.count(0xB5)
            n_trail += len(trail)
            n_bare += len(bare)
            for (off, lead, t) in trail:
                key = ('G%02d.I%03d' % (g + 1, i)) if g is not None else ('NODE%04d' % i)
                detail.append(dict(key=key, g=g, i=i, off=off, lead=lead, trail=t))
        used_pairs[tag] = pair_used
        per_tag[tag] = dict(
            n_entries=len(ents), payload_bytes=tot, bare_B1=n_b1, bare_B5=n_b5,
            entries_with_either=n_ent_with, as_trail=n_trail, bare_single=n_bare,
            n_distinct_pairs_present=len(pair_used),
            n_distinct_sentinel_trail=len(set((d['lead'], d['trail']) for d in detail)),
            n_distinct_chars=len(set(cs.pair_of.get((d['lead'], d['trail'])) for d in detail)),
            detail=detail)
        report.setdefault('containers', {})[tag] = {k: v for k, v in per_tag[tag].items()
                                                    if k != 'detail'}
        L.log('%-26s entries=%5d payload=%7d  B1=%4d B5=%4d  entries_with=%4d  '
              'trail=%4d bare=%4d  distinct_pairs=%4d'
              % (tag, len(ents), tot, n_b1, n_b5, n_ent_with, n_trail, n_bare, len(pair_used)))

    # XML：<text> 之外还有没有哨兵
    xc = conts['EN_SPECIAL_FEATURE.XML']
    xblob = xc['blob']
    spans = L.xml_text_spans(xblob)
    in_text = set()
    for (s, e) in spans:
        in_text |= set(range(s, e))
    all_hits = [off for off in range(len(xblob)) if xblob[off] in L.SENTINELS]
    report['xml'] = dict(blob_bytes=len(xblob), n_text_nodes=len(spans),
                         n_sentinel_bytes_total=len(all_hits),
                         n_sentinel_in_text=sum(1 for o in all_hits if o in in_text),
                         n_sentinel_outside_text=sum(1 for o in all_hits if o not in in_text),
                         sentinel_offsets_outside_text=[o for o in all_hits if o not in in_text])
    L.log('XML 哨兵字节 %d（<text> 内 %d / 外 %d）'
          % (len(all_hits), report['xml']['n_sentinel_in_text'],
             report['xml']['n_sentinel_outside_text']))

    # ── 替代表（与 sent_build.py 同一确定性规则）──
    _s2 = importlib.util.spec_from_file_location(
        'sb', os.path.join(HERE, 'sent_build.py'))
    SB = importlib.util.module_from_spec(_s2)
    _s2.loader.exec_module(SB)
    _tabs = SB.width_tables()
    _sent = set()
    for _t, _d in per_tag.items():
        for _r in _d['detail']:
            _sent.add((_r['lead'], _r['trail']))
    _union = set()
    for _v in used_pairs.values():
        _union |= _v
    _plan, _free = SB.choose_pairs(_sent, _union, _tabs)
    alias = {k: tuple(v['new']) for k, v in _plan.items()}
    report['alias'] = {'%02X%02X' % k: '%02X%02X' % v for k, v in sorted(alias.items())}
    L.log('替代表条目数 = %d' % len(alias))
    for (l, t), (l2, t2) in sorted(alias.items()):
        L.log('   (%02X,%02X) %s -> (%02X,%02X) %s'
              % (l, t, cs.pair_of.get((l, t)), l2, t2, cs.pair_of.get((l2, t2))))

    # ── 逐处清单（带 char / 替换值）──
    worst = 0
    for tag, d in per_tag.items():
        for rec in d['detail']:
            key = (rec['lead'], rec['trail'])
            nl, nt = alias[key]
            ch = cs.pair_of.get(key)
            fh.write('%s,%s,%s,%s,%d,%02X,%02X,%s,%02X,%02X%02X,%s,%s\n'
                     % (tag, 'LANG' if rec['g'] is not None else 'XML',
                        rec['key'] if rec['g'] is not None else '-',
                        rec['i'], rec['off'], rec['lead'], rec['trail'], ch,
                        nt, nl, nt, 'yes',
                        ','.join('%02X' % b for b in L.entries_of(conts[tag])[rec['i']][3]
                                 if b in L.SENTINELS) if rec['g'] is not None else '-'))
            worst = max(worst, abs(nt - rec['trail']))
    fh.close()
    report['substitution_stats'] = dict(max_trail_shift=worst)

    # ── 合计 ──
    report['totals'] = dict(
        trail=sum(d['as_trail'] for d in per_tag.values()),
        bare=sum(d['bare_single'] for d in per_tag.values()),
        sentinel_bytes=sum(d['bare_B1'] + d['bare_B5'] for d in per_tag.values()),
        lang_trail=sum(per_tag[t]['as_trail'] for t in per_tag if t != 'EN_SPECIAL_FEATURE.XML'),
        xml_trail=per_tag['EN_SPECIAL_FEATURE.XML']['as_trail'])
    L.log('合计：哨兵字节 %d = trail %d + 裸 %d；其中 LANG trail %d / XML trail %d'
          % (report['totals']['sentinel_bytes'], report['totals']['trail'],
             report['totals']['bare'], report['totals']['lang_trail'],
             report['totals']['xml_trail']))

    # 两 LANG 容器是否逐字节相同
    report['lang_blobs_identical'] = (conts['EN_STRINGS.RES@MENU']['blob'] ==
                                      conts['EN_STRINGS.RES@GR']['blob'])
    L.log('两个 LANG 容器 blob 逐字节相同 = %s' % report['lang_blobs_identical'])

    L.write_json(os.path.join(L.AUD, 'A_sentinel_scan.json'), report)
    L.log('[out] %s' % os.path.join(L.AUD, 'A_sentinel_scan.json'))


if __name__ == '__main__':
    main()
