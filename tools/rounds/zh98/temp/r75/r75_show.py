# -*- coding: utf-8 -*-
"""r75_show.py -- print selected parts of loader30.json (helper, read-only)."""
import json
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, 'loader30.json')
d = json.load(open(P, encoding='utf-8'))
want = sys.argv[1:] or ['sites']
if 'sites' in want:
    for k, v in d['sites'].items():
        print('###', k, ' sym=', v['sym'])
        print('\n'.join(v['text']))
        print()
if 'acct' in want:
    for k, v in d['accounting'].items():
        print('###', k)
        print(json.dumps(v, indent=1, ensure_ascii=False)[:3000])
        print()
