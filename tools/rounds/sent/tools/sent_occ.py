# -*- coding: utf-8 -*-
r"""sent_occ.py —— 对偶码占用普查（只读）：每个 lead 用了多少 trail、哪些 lead 已满。"""
import os
import sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sent_lib as L                                                     # noqa: E402
import tcslib as T                                                       # noqa: E402
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

conts = L.load_all()
used = {t: set() for t in conts}
for tag, c in conts.items():
    for (g, i, ln, data) in L.entries_of(c):
        _tr, _ba, pairs = L.scan_payload(data)
        used[tag] |= pairs
union = set()
for s in used.values():
    union |= s
print('used pairs: MENU=%d GR=%d XML=%d union=%d / 2350'
      % (len(used['EN_STRINGS.RES@MENU']), len(used['EN_STRINGS.RES@GR']),
         len(used['EN_SPECIAL_FEATURE.XML']), len(union)))
print()
print('lead  used(union)  free  sentinel_used  sent_chars_used  free_after_vacating_sentinels')
cs = T.Charset()
sent_by_lead = {}
for (l, t) in union:
    if t in L.SENTINELS:
        sent_by_lead.setdefault(l, set()).add(t)
for lead in range(L.LEAD_LO, L.PRESENT_LEAD_HI):
    u = [t for (l, t) in union if l == lead]
    sent = sent_by_lead.get(lead, set())
    print('0x%02X   %3d        %3d    %s        %d'
          % (lead, len(u), 94 - len(u), sorted('%02X' % x for x in sent), len(sent)))
print()
# 整个空间里 sentinel 相关字是否被用到
sent_pair_used = sorted([(hex(l), hex(t), cs.pair_of.get((l, t))) for (l, t) in union
                         if t in L.SENTINELS], key=lambda x: (x[0], x[1]))
print('载荷里出现的哨兵对偶码 %d 个：' % len(sent_pair_used))
print('   ', sent_pair_used)
print()
print('全空间空闲对偶码（union 里没有的）= %d' % (2350 - len(union)))
print('其中每个 lead 的空闲 trail:')
for lead in range(L.LEAD_LO, L.PRESENT_LEAD_HI):
    fr = [t for t in range(L.TRAIL_LO, L.TRAIL_HI + 1)
          if (lead, t) not in union and t not in L.SENTINELS]
    print('  0x%02X: %3d  free=%s' % (lead, len(fr),
                                      ' '.join('%02X' % x for x in fr[:24]) +
                                      (' ...' if len(fr) > 24 else '')))
