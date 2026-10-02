# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
from res_encode import parse_expanded, esc

gr  = parse_expanded(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_en_strings_expanded.bin'),'rb').read())
menu= parse_expanded(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'en_strings_res_expanded.bin'),'rb').read())

print('GR  : groups=%d entries=%d' % (len(gr), sum(len(g.strings) for g in gr)))
print('MENU: groups=%d entries=%d' % (len(menu), sum(len(g.strings) for g in menu)))
print('per-group counts identical:', [len(g.strings) for g in gr]==[len(g.strings) for g in menu])
print('sep/extras identical:', [(g.sep,g.extras) for g in gr]==[(g.sep,g.extras) for g in menu])

# 条目级对比
diffs = []
for gi,(g1,g2) in enumerate(zip(gr,menu),1):
    for si,(s1,s2) in enumerate(zip(g1.strings,g2.strings)):
        if s1 != s2:
            diffs.append((gi,si,s1[0],s2[0],s1[1],s2[1]))
print('entry diffs: %d' % len(diffs))
tot_delta = 0
for gi,si,b1,b2,a1,a2 in diffs:
    d = len(b1)-len(b2)
    tot_delta += d
    print('G%02d.I%03d len %d vs %d (Δ%+d) attr %04X/%04X' % (gi,si,len(b1),len(b2),d,a1,a2))
    print('   GR  : %s' % b1.decode('latin-1','replace')[:200])
    print('   MENU: %s' % b2.decode('latin-1','replace')[:200])
print('total length delta from diffs: %+d' % tot_delta)

# 高位字节统计
hi = {}
for g in gr:
    for s,_ in g.strings:
        for b in s:
            if b > 0x7E: hi[b] = hi.get(b,0)+1
print('high bytes:', {'0x%02X'%k:v for k,v in sorted(hi.items())})
nul = sum(1 for g in gr for s,_ in g.strings if b'\x00' in s)
empty = sum(1 for g in gr for s,_ in g.strings if len(s)==0)
print('entries containing 0x00: %d ; empty entries: %d' % (nul, empty))
# {p} 标记统计
ptag = sum(1 for g in gr for s,_ in g.strings if b'{p}' in s)
print('entries containing {p}: %d' % ptag)
