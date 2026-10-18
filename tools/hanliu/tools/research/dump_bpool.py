# -*- coding: utf-8 -*-
"""Dump b-pool: groups[57],[58],[60],[61],[64] entries with len<=30."""
import os as _os_pr
REPO_ROOT = _os_pr.path.abspath(_os_pr.path.join(_os_pr.path.dirname(_os_pr.path.abspath(__file__)), '..', '..', '..', '..'))

import json, collections

data = json.load(open(os.path.join(REPO_ROOT, 'work', 'tmp', 'hanzi_demand', 'res_parsed.json'), encoding='utf-8'))
groups = data['groups']
POOL = [57, 58, 60, 61, 64]
NAMES = {57: 'main_ui_pool(G58)', 58: 'menu_mp_ui(G59)', 60: 'control_labels(G61)',
         61: 'credits(G62)', 64: 'options_ui(G65)'}

rows = []
for gi in POOL:
    for e in groups[gi]['entries']:
        if e['len'] <= 30:
            rows.append((gi, e['i'], e['len'], e['text']))

print('total entries in pool groups:', sum(groups[gi]['count'] for gi in POOL))
print('entries with len<=30:', len(rows))
uniq = collections.Counter(t for _,_,_,t in rows)
print('unique strings:', len(uniq))

# classify: needs hanzi? has letters?
def has_letters(t): return any(c.isalpha() and ord(c) < 128 for c in t)
noletters = [t for t in uniq if not has_letters(t)]
print('unique without ASCII letters (numbers/punct/symbols):', len(noletters))
withletters = sorted(t for t in uniq if has_letters(t))
print('unique with letters:', len(withletters))
for t in withletters:
    print(repr(t))
print('--- no-letter uniques ---')
for t in sorted(noletters):
    print(repr(t))
json.dump(rows, open(os.path.join(REPO_ROOT, 'work', 'tmp', 'hanzi_demand', 'bpool_rows.json'), 'w', encoding='utf-8'))
