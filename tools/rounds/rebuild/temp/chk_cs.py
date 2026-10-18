# -*- coding: utf-8 -*-
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..'))
for rel in (r'tools\font_pipeline\data\charset_compiled_zh16.json',
            r'work\builds\GR_HASHR\backup\charset_compiled_zh16.json.before_hashr'):
    p = os.path.join(REPO, rel)
    d = json.load(io.open(p, encoding='utf-8'))
    po = d.get('pair_of')
    codes = d.get('codes')
    print('%-64s size=%d' % (rel, os.path.getsize(p)))
    print('    pair_of 条数 = %s ; codes 条数 = %s ; reserved_slots = %s' %
          (len(po) if po is not None else None,
           len(codes) if codes is not None else None, d.get('reserved_slots')))
    if isinstance(po, dict):
        ks = list(po.keys())
        print('    样例键: %r -> %r' % (ks[0], po[ks[0]]))
