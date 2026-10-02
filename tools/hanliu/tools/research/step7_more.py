# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
import gr_lz
data, ents = gr_lz.load_entries(os.path.join(REPO_ROOT, 'work', 'tmp', 'GR.img'))

print('=== 全部 .RES / .TXT / .MIS / .KIT / FONT* 条目 ===')
for e in ents:
    n = e['name'].upper()
    if n.endswith(('.RES','.TXT','.MIS')) or 'FONT' in n:
        print('  %-28s off=%-12d stored=%-9d real=%-9d %s' % (e['name'], e['off'], e['stored'], e['real'],
              'LZ' if e['stored']!=e['real'] else 'plain'))

print('\n=== KIT 抽样 (明文, 141 条) ===')
def head(name, n=200):
    e = [x for x in ents if x['name']==name][0]
    b = data[e['off']:e['off']+min(n,e['stored'])]
    return b.decode('latin-1','replace').replace('\r','').replace('\n','\n')[:200]
for nm in [x['name'] for x in ents if x['name'].upper().endswith('.KIT')][:3]:
    print('  %s | %s' % (nm, head(nm)))

print('\n=== SH/SS/SB/PSS 头 32 字节 (magic 判断) ===')
import struct
for ext in ('SH','SS','SB','PSS','RSB','VCL','PRJ','IDC'):
    e = [x for x in ents if x['name'].upper().endswith('.'+ext) and x['stored']==x['real']]
    if not e: continue
    e = e[0]
    b = data[e['off']:e['off']+16]
    print('  %-24s plain=%d  head=%s' % (e['name'], e['stored']==e['real'], b[:16].hex(' ')))
