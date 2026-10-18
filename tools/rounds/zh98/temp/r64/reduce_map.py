# -*- coding: utf-8 -*-
r"""reduce_map.py — 生成**改写对照表** reduce_map.csv (供用户复核语气是否走样)

做法 (全部机械可复现, 不靠人写):
  1. 用 difflib 对齐 `old/<id>.txt` (改写前) 与 `new/<id>.txt` (改写后);
  2. 每个 replace / delete / insert 区块出一行;
  3. 「替换了哪些超范围字」= 该区块**原文片段**里不在字库内的字 (去重);
  4. 「手法」= 该区块里**实际命中**的替换规则 (原文片段与改后片段同时出现的规则),
     最多列 3 条, 形如 `同义替换: 授予→发给`; 没有可归因规则时写 `改写/语序调整`。

输出列: 条目id | 原文片段 | 改后片段 | 替换了哪些超范围字 | 用了什么同义/改写手法
"""
import csv
import difflib
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_lib as L                                                # noqa: E402
import reduce_rules as R                                              # noqa: E402
from reduce_apply import srt                                           # noqa: E402

OLD = os.path.join(HERE, 'old')
NEW = os.path.join(HERE, 'new')
TGT = os.path.join(HERE, 'reduce_targets.json')
OUT = os.path.join(HERE, 'reduce_map.csv')
CTX = 6                       # 区块两侧各带多少字上下文 (便于看懂)


def read(p):
    t = io.open(p, encoding='utf-8', newline='').read()
    return t[:-1] if t.endswith('\n') else t


def rules_hit(old_frag, new_frag, rid):
    """这个区块里哪些替换规则真的生效了 (原文片段与改后片段同时出现)。"""
    hits = []
    for pat, rep in srt(R.PER.get(rid, [])) + srt(R.GLOB):
        if pat in old_frag and rep and rep in new_frag:
            hits.append('%s→%s' % (pat, rep))
    return hits


def main():
    d = json.load(io.open(TGT, encoding='utf-8'))
    rows, stat = [], dict(blocks=0, chars=0, kinds=set())
    for rid in sorted(d):
        a = read(os.path.join(OLD, rid.replace(':', '_') + '.txt'))
        b = read(os.path.join(NEW, rid.replace(':', '_') + '.txt'))
        sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == 'equal':
                continue
            stat['blocks'] += 1
            o = a[i1:i2]
            n = b[j1:j2]
            miss = ''.join(L.missing_of(o))
            stat['kinds'] |= set(miss)
            stat['chars'] += L.missing_count(o)
            hits = rules_hit(a[max(0, i1 - CTX):i2 + CTX],
                             b[max(0, j1 - CTX):j2 + CTX], rid)
            method = ('同义替换: ' + '; '.join(hits[:3])) if hits else '改写/语序调整'
            # 带一点上下文, 便于人读
            oc = a[max(0, i1 - CTX):i1] + o + a[i2:i2 + CTX]
            nc = b[max(0, j1 - CTX):j1] + n + b[j2:j2 + CTX]
            rows.append([rid, oc.replace('\n', '⏎'), nc.replace('\n', '⏎'),
                         miss or '-', method])
    with io.open(OUT, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['条目id', '原文片段(带上下文)', '改后片段(带上下文)',
                    '替换了哪些超范围字', '用了什么同义/改写手法'])
        w.writerows(rows)
    print('→ %s' % OUT)
    print('   %d 处改动区块; 涉及超范围字 %d 种 / %d 次'
          % (stat['blocks'], len(stat['kinds']), stat['chars']))


if __name__ == '__main__':
    main()
