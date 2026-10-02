# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
import gr_lz, lz77_decode
data, ents = gr_lz.load_entries(os.path.join(REPO_ROOT, 'work', 'tmp', 'GR.img'))

def dec(name):
    e = [x for x in ents if x['name']==name][0]
    raw = data[e['off']:e['off']+e['stored']]
    out, st = lz77_decode.decode_entry(raw)
    bad=[s for s in st if s[3]]
    print('%s: stored=%d real=%d subs=%d decoded=%d err=%d' % (name,e['stored'],e['real'],len(st),len(out),len(bad)))
    return out

t = dec('STRINGS.TXT')
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_STRINGS_TXT.dec'),'wb').write(t)
print(t[:1500].decode('latin-1','replace'))
print('...')
print(t[-800:].decode('latin-1','replace'))

f = dec('FONT.RES')
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_FONT_RES.dec'),'wb').write(f)
print('\nFONT.RES head:', f[:48].hex(' '))

i = dec('IKE.RES')
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_IKE_RES.dec'),'wb').write(i)
print('IKE.RES head:', i[:32].hex(' '), i[32:64])

# 明文 XML 家族精确计数
import re
from collections import defaultdict
fam = defaultdict(lambda:[0,0])
for e in ents:
    if e['stored']!=e['real']: continue
    b = data[e['off']:e['off']+min(64,e['stored'])]
    if b[:1]==b'<':
        ext = e['name'].rsplit('.',1)[-1].upper()
        fam[ext][0]+=1; fam[ext][1]+=e['stored']
print('\n明文 XML 家族 (条数/字节):')
for k,v in sorted(fam.items(), key=lambda x:-x[1][0]):
    print('  %-5s %5d 条 %9d B' % (k, v[0], v[1]))
