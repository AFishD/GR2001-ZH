# -*- coding: utf-8 -*-
import os
import re
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', '..', '..', '..', 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', '..', '..', '..', '..', 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T
import font_usage as FU
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
iso = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'))
conts = FU.build_container_list(iso)
hit = [c for c in conts if c['name'] == 'D01_BEACH.SHT'][0]
blob, _r = FU.container_blob(iso, hit)
print('blob=%d kind=%s' % (len(blob), hit['kind']))
rx = re.compile(rb'[\x20-\x7e]{12,}')
ms = list(rx.finditer(blob))
print('L>=12 命中 %d' % len(ms))
for m in ms[:6]:
    print('   %8d %r' % (m.start(), m.group(0)[:70]))
rx2 = re.compile(rb'[\x20-\x7e]{16,}')
print('L>=16 命中 %d' % len(list(rx2.finditer(blob))))
hit2 = [c for c in conts if c['name'] == 'D01_BEACH.MIS'][0]
b2, _r2 = FU.container_blob(iso, hit2)
print('\nMIS blob=%d' % len(b2))
ms2 = list(rx2.finditer(b2))
print('L>=16 命中 %d' % len(ms2))
for m in ms2[:5]:
    print('   %8d %r' % (m.start(), m.group(0)[:70]))
iso.close()
