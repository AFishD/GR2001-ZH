# -*- coding: utf-8 -*-
r"""hg1_dump.py — 只读: 导出 EN/ZH 的 MENU+GR FONT.RES 三面记录表，供"取回 vs 外推"决策。

产出: work/builds/GR_HUGE/evidence/hg1_faces.txt (人读)
      work/builds/GR_HUGE/evidence/hg1_faces.json (机读, 含全部记录矩形)
"""
import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hg_lib as H      # noqa: E402

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')


def main():
    lines = []
    W = lines.append
    data = {}
    plains = {}
    for tag in ('EN_ORIG', 'ZH113b'):
        for imgk in ('MENU', 'GR'):
            d = H.fontres(tag, imgk)
            plains[(tag, imgk)] = d['plain']
            key = '%s/%s' % (tag, imgk)
            e = d['entry']
            W('=' * 100)
            W('%s  entry idx=%d stored=%d real=%d off=0x%X  base=0x%X' %
              (key, e['idx'], e['stored'], e['real'], e['off'], d['base']))
            W('     comp=%d internal_real=%d plain_len=%d nfaces=%d styles_off=0x%X'
              % (d['comp'], d['real'], len(d['plain']), d['nfaces'], d['styles_off']))
            rec = dict(entry_idx=e['idx'], stored=e['stored'], real_entry=e['real'],
                       off=e['off'], base=d['base'], comp=d['comp'], real_internal=d['real'],
                       plain_len=len(d['plain']), styles_off=d['styles_off'],
                       nfaces=d['nfaces'], iso_off=d['base'] + e['off'],
                       slot_tail_zero=sum(1 for x in d['raw'][8 + d['comp']:] if x == 0),
                       slot_tail=len(d['raw']) - 8 - d['comp'], faces={})
            for f in d['faces']:
                rs = [list(H.rec_at(f, i)) for i in range(f['nr'])]
                c = Counter((r[4] - r[2], r[5] - r[3]) for r in rs)
                W('  face %-8s fld_off=0x%04X rec_off=0x%04X nrec=%3d (fld[4]=%d fld[5]=%d)'
                  % (f['name'], f['fld_off'], f['rec_off'], f['nr'], f['fld'][4], f['fld'][5]))
                W('       fld = %s' % f['fld'])
                W('       rect (w x h) mode: %s' % (c.most_common(4),))
                rec['faces'][f['name']] = dict(nr=f['nr'], fld=f['fld'],
                                               fld_off=f['fld_off'], rec_off=f['rec_off'],
                                               rects=rs)
                for i in (0, 1, 2, 95, 96, 97, 223):
                    if i < f['nr']:
                        W('       rec[%3d] = %s' % (i, rs[i]))
            W('  styles_off=0x%X  styles(first 64B) = %s'
              % (d['styles_off'], d['plain'][d['styles_off']:d['styles_off'] + 64].hex(' ')))
            W('  slot tail: %d B (all-zero %d B)' % (rec['slot_tail'], rec['slot_tail_zero']))
            data[key] = rec

    W('')
    W('=' * 100)
    W('* EN huge rec[0..95] vs ZH huge rec[0..95] record-by-record')
    en = data['EN_ORIG/MENU']['faces']['huge']['rects']
    zh = data['ZH113b/MENU']['faces']['huge']['rects']
    W('  identical %d / 96' % sum(1 for i in range(96) if en[i] == zh[i]))
    W('  EN huge rec[96..223] (first 8 + last 4):')
    for i in list(range(96, 104)) + list(range(220, 224)):
        W('    rec[%3d] = %s' % (i, en[i]))
    W('  EN huge rec[96..223] rect mode: %s'
      % (Counter((r[4] - r[2], r[5] - r[3]) for r in en[96:224]).most_common(6),))
    W('  EN huge rec[0..95]  rect mode: %s'
      % (Counter((r[4] - r[2], r[5] - r[3]) for r in en[0:96]).most_common(6),))
    W('  ZH huge rec[0..95]  rect mode: %s'
      % (Counter((r[4] - r[2], r[5] - r[3]) for r in zh).most_common(6),))

    W('')
    W('* GR: EN huge rec[0..95] vs ZH huge rec[0..95]')
    en2 = data['EN_ORIG/GR']['faces']['huge']['rects']
    zh2 = data['ZH113b/GR']['faces']['huge']['rects']
    W('  identical %d / 96' % sum(1 for i in range(96) if en2[i] == zh2[i]))
    W('  EN huge rec[96..223] rect mode: %s'
      % (Counter((r[4] - r[2], r[5] - r[3]) for r in en2[96:224]).most_common(6),))

    W('')
    W('* MENU vs GR: is the FONT.RES plaintext byte-identical')
    for tag in ('EN_ORIG', 'ZH113b'):
        p1 = plains[(tag, 'MENU')]
        p2 = plains[(tag, 'GR')]
        W('  %s: %s (len %d vs %d)' % (tag, 'SAME' if p1 == p2 else 'DIFFERENT',
                                       len(p1), len(p2)))

    W('')
    W('* ZH huge rec[0..95] full table (MENU)')
    for i in range(96):
        W('    rec[%3d] = %s' % (i, zh[i]))
    W('')
    W('* EN huge rec[96..223] full table (MENU)')
    for i in range(96, 224):
        W('    rec[%3d] = %s' % (i, en[i]))
    W('')
    W('* ZH default rec[96..223] full table (MENU)  [fallback plan B source]')
    zd = data['ZH113b/MENU']['faces']['default']['rects']
    for i in range(96, 224):
        W('    rec[%3d] = %s' % (i, zd[i]))

    os.makedirs(H.EVID, exist_ok=True)
    open(os.path.join(H.EVID, 'hg1_faces.txt'), 'w', encoding='utf-8').write('\n'.join(lines))
    open(os.path.join(H.EVID, 'hg1_faces.json'), 'w', encoding='utf-8').write(
        json.dumps(data, ensure_ascii=False, indent=1))
    print('wrote hg1_faces.txt (%d lines)' % len(lines))


if __name__ == '__main__':
    main()
