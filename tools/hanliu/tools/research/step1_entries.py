# -*- coding: utf-8 -*-
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import sys, json
sys.path.insert(0, os.path.join(REPO_ROOT, 'tools', 'gr_tools'))
import gr_lz

data, ents = gr_lz.load_entries(os.path.join(REPO_ROOT, 'work', 'tmp', 'GR.img'))
print('total entries:', len(ents))
strs = [e for e in ents if e['name'].upper().endswith('_STRINGS.RES') or 'STRING' in e['name'].upper()]
for e in strs:
    print('%-24s off=%-12d stored=%-9d real=%-9d %s' % (e['name'], e['off'], e['stored'], e['real'],
          'COMPRESSED' if e['stored']!=e['real'] else 'plain'))

# 整体统计
comp = [e for e in ents if e['stored'] != e['real']]
plain = [e for e in ents if e['stored'] == e['real']]
print('\nentries total=%d compressed=%d plain=%d' % (len(ents), len(comp), len(plain)))
tot_s = sum(e['stored'] for e in ents); tot_r = sum(e['real'] for e in ents)
print('sum stored=%d sum real=%d ratio=%.1f%%' % (tot_s, tot_r, 100.0*tot_s/tot_r))

# 扩展名分布 (plain 明文资源普查素材)
from collections import Counter
ext = Counter()
for e in ents:
    n = e['name']
    ex = n.rsplit('.',1)[-1].upper() if '.' in n else '(none)'
    ext[ex] += 1
print('\nextension distribution:')
for k, v in ext.most_common():
    print('  %-8s %d' % (k, v))
