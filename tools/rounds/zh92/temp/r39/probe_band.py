# -*- coding: utf-8 -*-
"""r39: 抽查 clean_ratio 落在 [0.002,0.005) 的容器 —— 到底是真串还是噪声。只读。"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU
import dump_containers as DC

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ZH)
cs = T.Charset()
DC._IDX = FU.CharsetIndex()
conts = FU.build_container_list(iso)
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
keep = [x for x in D if x['risk'] and x['distinct'] >= 10 and x['score'] >= 10
        and x['clean_ratio'] >= 0.002]
band = sorted([x for x in keep if 0.002 <= x['clean_ratio'] < 0.005],
              key=lambda y: -y['distinct'])
print('band 容器数 %d' % len(band))
by = {}
for c in conts:
    by.setdefault((c['img'], c['idx'], c['name']), c)
import random
random.seed(7)
for x in random.sample(band, min(9, len(band))):
    c = by[(x['img'], x['idx'], x['name'])]
    blob, _r = FU.container_blob(iso, c)
    r = DC.scan_container(blob, x['kind'], cs, cap=200000)
    ex = [y for y in r['rows'] if y['exact']]
    print('\n== %-9s %-30s blob=%8d distinct=%5d exact=%5d clean=%.5f =='
          % (x['kind'], x['name'][:30], len(blob), r['distinct'], len(ex), x['clean_ratio']))
    for y in r['rows'][:6]:
        print('      %8d %r' % (y['off'], y['text'][:90]))
    alnum = [y for y in r['rows'] if y['exact'] and y['text'].isalnum()]
    print('   纯字母数字的 exact 串: %d 条' % len(alnum))
    for y in alnum[:5]:
        print('      ALNUM %r' % y['text'][:70])
iso.close()
