# -*- coding: utf-8 -*-
"""r39: LOGOUBI.PSS 里到底是什么串 —— 决定 MEDIA 怎么处理。只读。"""
import os
import re
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
by = {}
for c in conts:
    by.setdefault((c['name'], c['kind']), c)

for nm, kd in (('LOGOUBI.PSS', 'MEDIA'), ('MUSIC.TM', 'MEDIA'), ('BNK_99_00.SS', 'MEDIA'),
               ('D01_BEACH.SHT', 'MEDIA')):
    c = by[(nm, kd)]
    blob, _r = FU.container_blob(iso, c)
    r = DC.scan_container(blob, kd, cs)
    mb = len(blob) / 1048576.0
    print('\n== %s  blob=%d (%.1f MB)  不同串 %d (=%.0f/MB)  ASCII 干净字节 %d =='
          % (nm, len(blob), mb, r['distinct'], r['distinct'] / mb, r['clean']))
    rs = sorted(r['rows'], key=lambda x: x['dup'])
    print('   -- 出现 1 次的串 (前 12) --')
    for x in [y for y in rs if y['dup'] == 1][:12]:
        print('      %8d %r' % (x['off'], x['text'][:100]))
    print('   -- 重复最多的串 (前 12) --')
    for x in sorted(r['rows'], key=lambda y: -y['dup'])[:12]:
        print('      dup=%5d %8d %r' % (x['dup'], x['off'], x['text'][:100]))
    # 位置分布: 串集中在哪里?
    offs = sorted(x['off'] for x in r['rows'])
    if offs:
        print('   偏移分布: 首 %d 末 %d (blob %d) ⇒ 前 10%% 区域有 %d 条, 后 90%% 有 %d 条'
              % (offs[0], offs[-1], len(blob),
                 sum(1 for o in offs if o < len(blob) // 10),
                 sum(1 for o in offs if o >= len(blob) // 10)))
iso.close()
