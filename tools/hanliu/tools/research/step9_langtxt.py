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
    return out
en = dec('EN_STRINGS.TXT')
open(os.path.join(REPO_ROOT, 'work', 'tmp', 'gr_res', 'gr_EN_STRINGS_TXT.dec'),'wb').write(en)
de = dec('DE_STRINGS.TXT')
# 差异行数
import re
def lines(b): return [l for l in b.decode('latin-1','replace').splitlines() if l.strip() and not l.strip().startswith('//')]
le, ld = lines(en), lines(de)
print('EN_STRINGS.TXT lines=%d  DE lines=%d' % (len(le), len(ld)))
diff = [(a,b) for a,b in zip(le,ld) if a!=b]
print('EN vs DE differing lines: %d' % len(diff))
for a,b in diff[:6]:
    print('  EN : %s' % a.strip()[:90]); print('  DE : %s' % b.strip()[:90])
print('\nEN head:'); print('\n'.join(le[:12]))
