# -*- coding: utf-8 -*-
r"""_dbg_sf2.py — 逐字节对齐定位 EN_SPECIAL_FEATURE.XML 单位的差异机理（只读）"""
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

TAG = sys.argv[1] if len(sys.argv) > 1 else 'SPECIAL'
UNIT = int(sys.argv[2]) if len(sys.argv) > 2 else 331
iso_f, cf = V.load_conts(os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'GR_FA2400.iso'))
iso_b, cb = V.load_conts(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
_cN, pairN, _eN, _pN = V.pairs_of(T.CHARSET)
_cH, pairH, _eH, _pH = V.pairs_of(V.HIST_CS)

for (A, Bl) in zip(cb, cf):
    if TAG not in A['tag']:
        continue
    ra, _ua, _ia = ML.payload_ranges(A)
    rb, _ub, _ib = ML.payload_ranges(Bl)
    x, y = ra[UNIT], rb[UNIT]
    pb = A['blob'][x[0]:x[1]]
    pf = Bl['blob'][y[0]:y[1]]
    print('unit %d : base[%d,%d) len %d ; final[%d,%d) len %d' % (UNIT, x[0], x[1], len(pb),
                                                                 y[0], y[1], len(pf)))
    # 前置上下文 (node 结构)
    print('base  前 24B: %s' % A['blob'][x[0] - 24:x[0]].hex())
    print('final 前 24B: %s' % Bl['blob'][y[0] - 24:y[0]].hex())
    print('base  后 24B: %s' % A['blob'][x[1]:x[1] + 24].hex())
    print('final 后 24B: %s' % Bl['blob'][y[1]:y[1] + 24].hex())
    k = 0
    while k < min(len(pb), len(pf)) and pb[k] == pf[k]:
        k += 1
    print('共同前缀 = %d B' % k)
    print('base  [%d:]: %s' % (max(0, k - 8), pb[max(0, k - 8):].hex()))
    print('final [%d:]: %s' % (max(0, k - 8), pf[max(0, k - 8):].hex()))
    for (nm, data, gate, ph, cs) in (('base ', pb, V.BASE_GATE, pairH, _cH),
                                     ('final', pf, V.GATE, pairN, _cN)):
        txt, mp = ML.decode_with(data, gate, ph, cs)
        print('%s txt(%d chars): %r' % (nm, len(txt), txt))
        print('%s 逐字符(前 40): %s' % (nm, ' '.join(
            '%s@%d(%d)' % (repr(txt[i]), mp[i][0], mp[i][1]) for i in range(min(40, len(txt))))))
iso_f.close()
iso_b.close()
