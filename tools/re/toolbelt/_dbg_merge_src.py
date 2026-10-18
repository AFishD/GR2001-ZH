# -*- coding: utf-8 -*-
r"""_dbg_merge_src.py — 追查 SFXML 乱码的来源: GR_TXMIG / GR_MERGE2400 / GR_FA2400 三者对照（只读）"""
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

_cN, pairN, _eN, _pN = V.pairs_of(T.CHARSET)
_cH, pairH, _eH, _pH = V.pairs_of(V.HIST_CS)
B = lambda *a: os.path.join(REPO, 'work', 'builds', *a)
ISOS = [('ZH113b(基底)', B('GR_ZH113b', 'GR_ZH113b.iso')),
        ('TXMIG(B 路)', B('GR_TXMIG', 'GR_TXMIG.iso')),
        ('MERGE2400', B('GR_MERGE2400', 'GR_MERGE2400.iso')),
        ('FA2400(成品)', B('GR_FA2400', 'GR_FA2400.iso'))]
loaded = {}
for (nm, p) in ISOS:
    iso, conts = V.load_conts(p)
    loaded[nm] = (iso, conts)
    print('== %-14s %s' % (nm, p))
    for c in conts:
        print('   %-26s iso_off 0x%08X stored %6d blob %6d sha %s'
              % (c['tag'], c['iso_off'], c['slot'], len(c['blob']),
                 __import__('hashlib').sha256(c['blob']).hexdigest()[:16]))
print()
base = dict((c['tag'], c) for c in loaded['ZH113b(基底)'][1])
for nm in ('TXMIG(B 路)', 'MERGE2400', 'FA2400(成品)'):
    print('== %s : 与基底逐 unit 对照 (INV 逆映射)' % nm)
    for c in loaded[nm][1]:
        cb = base[c['tag']]
        rb, _u, _i = ML.payload_ranges(cb)
        rf, _u2, _i2 = ML.payload_ranges(c)
        assert len(rb) == len(rf)
        nbad = 0
        first = []
        for k, (x, y) in enumerate(zip(rb, rf)):
            pb = cb['blob'][x[0]:x[1]]
            pf = c['blob'][y[0]:y[1]]
            rec, st = V.reconstruct(pf, pairN, dict(inv={v: 0 for v in V.INV.values()},
                                                    kept_pair=0, single=0, ascii=0,
                                                    orphan_lead=[], unknown_pair=[]))
            if rec != pb:
                nbad += 1
                if len(first) < 3:
                    first.append(k)
        print('   %-26s 单元 %4d ; 还原!=基底 %4d %s  首几个: %s'
              % (c['tag'], len(rf), nbad, '✓' if nbad == 0 else '✗', first))
for (nm, (iso, _c)) in loaded.items():
    iso.close()
