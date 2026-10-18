# -*- coding: utf-8 -*-
r"""r71j_charset_meta.py — 看 charset JSON 里的成对码/回收/扩容记录 (step3 依据)"""
import io
import json
import os
import sys
from collections import Counter

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
d = json.load(io.open(CS, encoding='utf-8'))

print('mode =', d['mode'])
print('grid =', json.dumps(d['grid'], ensure_ascii=False))
print('protected =', json.dumps(d['protected'], ensure_ascii=False))
print('mark_codes =', json.dumps(d['mark_codes'], ensure_ascii=False))
po = d['pair_of']
k0 = list(po.items())[:3]
print('pair_of 样例:', k0, '  ...共', len(po))
co = d['codes']
print('codes 样例:', list(co.items())[:5], ' ...共', len(co))
for k in ('_font_recycle_zh98', '_expand_zh113', '_font_compact'):
    print('\n== %s ==' % k)
    print(json.dumps(d[k], ensure_ascii=False)[:1500])
