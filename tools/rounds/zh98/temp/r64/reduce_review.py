# -*- coding: utf-8 -*-
r"""reduce_review.py — 改写质量自查: 逐条列出**每处替换的前后上下文**

用法:
  python reduce_review.py --rule 熟 拔 刺     # 只看这些"原文片段"命中的地方
  python reduce_review.py --deletions        # 只看**删字**规则 (替换为空) 命中的地方
  python reduce_review.py --id SFXML:T0069   # 只看某条目
  python reduce_review.py --count            # 只给每规则命中次数排行
只读, 不写盘。
"""
import io
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_rules as R                                              # noqa: E402
from reduce_apply import srt                                           # noqa: E402

OLD = os.path.join(HERE, 'old')
TGT = os.path.join(HERE, 'reduce_targets.json')


def main():
    a = sys.argv[1:]
    want = []
    if '--rule' in a:
        i = a.index('--rule')
        want = [x for x in a[i + 1:] if not x.startswith('--')]
    only_id = a[a.index('--id') + 1] if '--id' in a else None
    dels = '--deletions' in a
    cnt = Counter()
    ctx = defaultdict(list)
    d = json.load(io.open(TGT, encoding='utf-8'))
    for rid in sorted(d):
        if only_id and rid != only_id:
            continue
        t = d[rid]['text']
        pos = list(range(len(t)))          # 当前字符 → 原文下标 (用于打印**原文**上下文)
        for rules in (R.PER.get(rid, []), R.GLOB):
            for pat, rep in srt(rules):
                show = (pat in want) if want else True
                if dels and rep != '':
                    show = False
                i = 0
                while True:
                    k = t.find(pat, i)
                    if k < 0:
                        break
                    if show:
                        o = pos[k]
                        o0 = d[rid]['text']
                        cnt[(pat, rep)] += 1
                        if len(ctx[(pat, rep)]) < 3:
                            ctx[(pat, rep)].append(
                                '%s: 现…%s【%s→%s】%s…  | 原…%s…'
                                % (rid, t[max(0, k - 12):k], pat, rep or '(删)',
                                   t[k + len(pat):k + len(pat) + 12],
                                   o0[max(0, o - 16):o + 16]))
                    pos[k:k + len(pat)] = [pos[k]] * len(rep)
                    t = t[:k] + rep + t[k + len(pat):]
                    i = k + len(rep)
    print('命中 %d 条规则, 共 %d 处' % (len(cnt), sum(cnt.values())))
    if '--count' in a:
        for (pat, rep), n in cnt.most_common(60):
            print('   %-16s → %-16s ×%d' % (pat, rep or '(删)', n))
        return
    for (pat, rep), n in sorted(cnt.items(), key=lambda x: -x[1]):
        print('── %r → %r  ×%d' % (pat, rep or '(删)', n))
        for c in ctx[(pat, rep)]:
            print('     %s' % c)


if __name__ == '__main__':
    main()
