# -*- coding: utf-8 -*-
r"""_dbg_sf3.py — 用 SequenceMatcher 列出 SFXML 单位的**逐字节编辑脚本**（只读）

把 base → final 的差异拆成 opcode，并给每个被替换的 base 片段附上「基底解码字 →
final 解码字」，用来判断迁移到底做错了什么（例如是否插入了多余字节导致对偶码整体移窗）。
"""
import difflib
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
N = int(sys.argv[2]) if len(sys.argv) > 2 else 6
iso_f, cf = V.load_conts(os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'GR_FA2400.iso'))
iso_b, cb = V.load_conts(os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso'))
_cN, pairN, _eN, _pN = V.pairs_of(T.CHARSET)
_cH, pairH, _eH, _pH = V.pairs_of(V.HIST_CS)
FROM_B = {v: k for k, v in V.FWD.items()}      # 基底单字节 → 新对偶码

for (A, Bl) in zip(cb, cf):
    if TAG not in A['tag']:
        continue
    ra, _ua, _ia = ML.payload_ranges(A)
    rb, _ub, _ib = ML.payload_ranges(Bl)
    print('== %s : %d 单元' % (A['tag'], len(ra)))
    shown = 0
    kinds = {}
    for k, (x, y) in enumerate(zip(ra, rb)):
        pb = A['blob'][x[0]:x[1]]
        pf = Bl['blob'][y[0]:y[1]]
        sm = difflib.SequenceMatcher(None, pb, pf, autojunk=False)
        ops = [o for o in sm.get_opcodes() if o[0] != 'equal']
        if not ops:
            continue
        # 分类每个 opcode
        desc = []
        for (tag, i1, i2, j1, j2) in ops:
            b = pb[i1:i2]
            f = pf[j1:j2]
            tb, _ = ML.decode_with(b, V.BASE_GATE, pairH, _cH)
            tf, _ = ML.decode_with(f, V.GATE, pairN, _cN)
            key = (tag, len(b), len(f), b.hex(), f.hex())
            kinds[key] = kinds.get(key, 0) + 1
            desc.append('%s base[%d:%d]=%s(%r) → final[%d:%d]=%s(%r)'
                        % (tag, i1, i2, b.hex(), tb, j1, j2, f.hex(), tf))
        if shown < N:
            shown += 1
            print('   unit %d (base len %d, final len %d):' % (k, len(pb), len(pf)))
            for d in desc:
                print('      %s' % d)
    kinds_sorted = sorted(kinds.items(), key=lambda kv: -kv[1])
    print('   ── opcode 分类统计 (前 12):')
    for (key, cnt) in kinds_sorted[:12]:
        tag, lb, lf, bh, fh = key
        print('      %-9s ×%-4d base %dB %s → final %dB %s' % (tag, cnt, lb, bh, lf, fh))
iso_f.close()
iso_b.close()
