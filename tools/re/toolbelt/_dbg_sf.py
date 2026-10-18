# -*- coding: utf-8 -*-
r"""_dbg_sf.py — 定位 EN_SPECIAL_FEATURE.XML 里「还原流 != 基底载荷」的载荷单元（只读）"""
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib as T                                                     # noqa: E402
import migrate_legacy as ML                                            # noqa: E402
import fa_verify as V                                                  # noqa: E402

iso_f, cf = V.load_conts(os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'GR_FA2400.iso'))
iso_b, cb = V.load_conts(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
_cN, pairN, _eN, _pN = V.pairs_of(T.CHARSET)
_cH, pairH, _eH, _pH = V.pairs_of(V.HIST_CS)

for (A, Bl) in zip(cb, cf):
    if 'SPECIAL' not in A['tag']:
        continue
    ra, ua, ia = ML.payload_ranges(A)
    rb, ub, ib = ML.payload_ranges(Bl)
    print('== %s : 单元 %d/%d ; used %d/%d ; info %s / %s' % (A['tag'], len(ra), len(rb), ua, ub, ia, ib))
    bad = []
    for k, (x, y) in enumerate(zip(ra, rb)):
        pb = A['blob'][x[0]:x[1]]
        pf = Bl['blob'][y[0]:y[1]]
        rec, st = V.reconstruct(pf, pairN, dict(inv={v: 0 for v in V.INV.values()},
                                                kept_pair=0, single=0, ascii=0,
                                                orphan_lead=[], unknown_pair=[]))
        if rec != pb:
            m = next((i for i in range(min(len(rec), len(pb))) if rec[i] != pb[i]),
                     min(len(rec), len(pb)))
            bad.append((k, x, y, pb, pf, rec, m, st))
    print('   不等的单元 = %d' % len(bad))
    for (k, x, y, pb, pf, rec, m, st) in bad[:12]:
        print('   --- unit %d  base[%d,%d) len %d ; final[%d,%d) len %d ; 首个不同 @%d'
              % (k, x[0], x[1], len(pb), y[0], y[1], len(pf), m))
        print('       base hex : %s' % pb[:60].hex())
        print('       final hex: %s' % pf[:80].hex())
        print('       recon hex: %s' % rec[:60].hex())
        tb, _ = ML.decode_with(pb, V.BASE_GATE, pairH, _cH)
        tf, _ = ML.decode_with(pf, V.GATE, pairN, _cN)
        tr, _ = ML.decode_with(rec, V.BASE_GATE, pairH, _cH)
        print('       base txt : %r' % tb[:120])
        print('       final txt: %r' % tf[:120])
        print('       recon txt: %r' % tr[:120])
        print('       stat: inv=%s kept=%d single=%d ascii=%d unknown=%s orphan=%s'
              % ({'0x%02X' % a: b for a, b in st['inv'].items() if b}, st['kept_pair'],
                 st['single'], st['ascii'], st['unknown_pair'][:3], st['orphan_lead'][:3]))
iso_f.close()
iso_b.close()
