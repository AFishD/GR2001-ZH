# -*- coding: utf-8 -*-
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

PR = re.compile(rb'[\x20-\x7e]{%d,}')


def longs(blob, L):
    n = b = 0
    s = set()
    for m in PR.finditer(blob):
        g = m.group(0)
        if len(g) < L:
            continue
        n += 1
        b += len(g)
        s.add(g)
    return n, b, len(s)


iso = T.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'))
conts = FU.build_container_list(iso)
by = {}
for c in conts:
    by.setdefault((c['name'], c['kind']), c)
print('by 大小 = %d' % len(by))
key = ('D01_BEACH.MIS', 'MIS')
print('key 在 by 里: %s' % (key in by))
c = by[key]
blob, _r = FU.container_blob(iso, c)
print('blob=%d  repr(name)=%r' % (len(blob), c['name']))
print('longs(blob,16) = %r' % (longs(blob, 16),))
print('longs(blob,12) = %r' % (longs(blob, 12),))
# 手工重算
rx = re.compile(rb'[\x20-\x7e]{16,}')
ms = list(rx.finditer(blob))
print('手工 L>=16 = %d, 字节 %d' % (len(ms), sum(len(m.group(0)) for m in ms)))
iso.close()
