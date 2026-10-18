# -*- coding: utf-8 -*-
r"""debug_sf_regions.py — SFXML 迁移落点按区域拆解 + 尾巴内容取证 (只读诊断)"""
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 're', 'toolbelt'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import migrate_legacy as M                                               # noqa: E402
import tcslib as T                                                       # noqa: E402

BASE, GATE = 0xB1, 0xBA
src = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
cs = T.Charset(T.CHARSET)
mp, extra = M.build_map(cs, BASE, GATE, {}, True, (GATE - T.LEAD_LO) * T.PAIR_STRIDE)
iso = T.Iso(src)
e = iso.img_entry(T.MENU_LBA, T.XML_IDX)
raw = iso.read(e['iso_off'], e['stored'])
blob = b''.join(s[0] for s in T.lzo_subs(raw))
iso.close()

texts = [(o, o + ln) for (_k, o, ln, _b) in T.parse_sfxml(blob)]
attrs = [(o, o + len(v)) for (_k, _t, o, v) in M._xml_attrs(blob)]
nodes = [(m.start(1), m.end(1)) for m in M.XML_NODE_RE.finditer(blob)]
nodes_nz = [(s, en) for (s, en) in nodes if blob[s:en].strip()]
used = T.xml_tail_start(blob)
out = {'blob': len(blob), 'used_end': used, 'n_text': len(texts), 'n_attr': len(attrs),
       'n_node': len(nodes), 'n_node_nonempty': len(nodes_nz)}


def cls_of(off):
    for (s, en) in texts:
        if s <= off < en:
            return 'text'
    for (s, en) in attrs:
        if s <= off < en:
            return 'attr(name=)'
    for (s, en) in nodes_nz:
        if s <= en and s <= off < en:
            return 'node'
    return 'outside'


# 与 migrate 同一套走法, 逐处记区域
cnt = {}
i, n = 0, len(blob)
while i < n:
    v = blob[i]
    if T.LEAD_LO <= v < BASE:
        i += 2
        continue
    if BASE <= v < GATE:
        cls = cls_of(i)
        cnt[cls] = cnt.get(cls, 0) + 1
    i += 1
out['raw_bytes_by_region'] = cnt

# 只在"引擎会渲染的区间"里按 dump 口径统计 (RE_NODE + studio/group name)
dump_rng = M.merge_ranges([(s, min(en, used)) for (s, en) in
                           (nodes_nz + [(m.start(2), m.end(2)) for m in
                                        re.finditer(rb'<(studio|group)\s+name="([^"]*)"', blob)])])
# 逐区域迁移计数 (与 migrate_payload 同走法, 但按区域分类)
mig = {}
for label, rngs in (('text', texts), ('attr(name=)', attrs),
                    ('node', nodes_nz), ('dump口径(RE_NODE+studio/group)', dump_rng)):
    tot = 0
    for (s, en) in M.merge_ranges([(a, min(b, used)) for (a, b) in rngs if a < used]):
        d, j, k = blob[s:en], 0, 0
        while j < len(d):
            x = d[j]
            if T.LEAD_LO <= x < BASE:
                j += 2
                continue
            if BASE <= x < GATE:
                k += 1
            j += 1
        tot += k
    mig[label] = tot
out['migrated_by_region'] = mig

# 尾巴内容取证
tail = blob[used:]
out['tail_len'] = len(tail)
out['tail_hex_head'] = tail[:64].hex()
out['tail_head'] = tail[:160].decode('latin-1')
out['tail_nonzero'] = sum(1 for x in tail if x)
out['tail_tail_hex'] = tail[-32:].hex()
out['tail_is_zeros'] = all(x == 0 for x in tail)

# dump_all_text 的 SF 抽取口径下, 0xB1..0xB9 落点 (对照 legacy_singles 的 59)
json.dump(out, io.open(os.path.join(HERE, 'recon_sf_regions.json'), 'w',
                       encoding='utf-8'), ensure_ascii=True, indent=1)
print(json.dumps({k: v for k, v in out.items() if k not in ('tail_head',)},
                 ensure_ascii=True, indent=1))
