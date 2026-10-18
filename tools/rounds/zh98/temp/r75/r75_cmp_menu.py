# -*- coding: utf-8 -*-
"""r75_cmp_menu.py -- compare MENU.IMG entry tables: shipping ZH disk vs EN original.

Answers: has this project ever *moved* an entry inside MENU.IMG (i.e. is relocation proven)?
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
a = json.load(open(os.path.join(HERE, 'menu_slack.json'), encoding='utf-8'))
b = json.load(open(os.path.join(HERE, 'menu_slack_en.json'), encoding='utf-8'))
A = {e['name']: e for e in a['entries']}
B = {e['name']: e for e in b['entries']}
print('ZH entries=%d  EN entries=%d' % (len(A), len(B)))
print('%-28s %-12s %-12s %-12s %-12s %s' % ('name', 'off_EN', 'off_ZH', 'stored_EN', 'stored_ZH', 'verdict'))
moved = 0
changed = 0
for nm in sorted(set(A) | set(B)):
    ea, eb = A.get(nm), B.get(nm)
    if not ea or not eb:
        print('%-28s ONLY-IN-%s' % (nm, 'ZH' if ea else 'EN'))
        continue
    same = (ea['off'] == eb['off'] and ea['stored'] == eb['stored'] and ea['real'] == eb['real'])
    if not same:
        changed += 1
        if ea['off'] != eb['off']:
            moved += 1
    print('%-28s 0x%08X   0x%08X   %-12d %-12d %s'
          % (nm, eb['off'], ea['off'], eb['stored'], ea['stored'],
             'SAME' if same else ('MOVED' if ea['off'] != eb['off'] else 'RESIZED')))
print('changed=%d  moved=%d' % (changed, moved))
