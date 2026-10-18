# -*- coding: utf-8 -*-
r"""p2_ftrect.py — 看 FT 记录矩形落在网格行上的**按 face** 明细 (决定保护范围)。"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                          # noqa: E402

W, H = 1024, 512
NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
j = json.load(open(os.path.join(HERE, 'p1_survey.json'), encoding='utf-8'))
cat = dict((int(k), v) for k, v in j['cat'].items())


def yrow(r):
    return tcslib.GRID_Y0 + CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


rows = sorted(set(s // NCOL for s in cat))
for face in ('large', 'default', 'huge'):
    rs = [r for r in j['rects'] if r['face'] == face]
    hit = []
    for r in rs:
        hr = [rr for rr in rows if yrow(rr) < r['v1'] and yrow(rr) + CH > r['v0']]
        if hr:
            hit.append((r, hr))
    print('=' * 70)
    print('face=%s  总记录 %d, 落在网格行带里的 %d' % (face, len(rs), len(hit)))
    seen = {}
    for r, hr in hit:
        for rr in hr:
            cols = [c for c in range(NCOL)
                    if CW * c < r['u1'] and r['u0'] < CW * (c + 1) and yrow(rr) < r['v1'] and r['v0'] < yrow(rr) + CH]
            seen.setdefault((rr, tuple(cols)), []).append('0x%02X' % r['code'])
    for (rr, cols), codes in sorted(seen.items()):
        print('   row%-3d cols=%-22s 记录码 %s' % (rr, list(cols), ' '.join(codes)))

# default face 的全部记录, 看 v0 分布
print('=' * 70)
import collections
c = collections.Counter(r['v0'] for r in j['rects'] if r['face'] == 'default')
print('default face 记录 v0 分布 (前 20): %s' % c.most_common(20))
