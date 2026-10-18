# -*- coding: utf-8 -*-
r"""reduce_todo.py — 给「按规则生成后仍超范围」的字生成**紧凑工作清单** (改写决策用)

输出 (按出现次数降序):
    <字> ×<次数>  <一个上下文>          ← 每个字只给一行, 上下文以该字为中心 ±10 字
用法:
  python reduce_todo.py                 # 全部剩余字
  python reduce_todo.py --top 120       # 只列前 120 个
  python reduce_todo.py --char 娜 砸    # 只看这几个字 (给全部上下文)
  python reduce_todo.py --table SFXML:T0069
只读, 不写盘。
"""
import io
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_lib as L                                                # noqa: E402
import reduce_rules as R                                              # noqa: E402
from reduce_apply import apply_rules                                  # noqa: E402

NEW = os.path.join(HERE, 'new')
TGT = os.path.join(HERE, 'reduce_targets.json')


def draft_of(rid, d):
    """当前改写稿 (new/ 有就用它, 否则用规则现算)。"""
    p = os.path.join(NEW, rid.replace(':', '_') + '.txt')
    if os.path.exists(p):
        t = io.open(p, encoding='utf-8', newline='').read()
        return t[:-1] if t.endswith('\n') else t
    t = d[rid]['text']
    return apply_rules(apply_rules(t, R.PER.get(rid, [])), R.GLOB)


def main():
    a = sys.argv[1:]
    top = None
    only = []
    table = None
    if '--top' in a:
        top = int(a[a.index('--top') + 1])
    if '--char' in a:
        only = [x for x in a[a.index('--char') + 1:] if not x.startswith('--')]
    if '--table' in a:
        table = a[a.index('--table') + 1]
    d = json.load(io.open(TGT, encoding='utf-8'))
    cnt, ctx = Counter(), {}
    for rid in sorted(d):
        if table and rid != table:
            continue
        t = draft_of(rid, d)
        for ch in L.missing_of(t):
            n = t.count(ch)
            cnt[ch] += n
            i = t.find(ch)
            a0, b0 = max(0, i - 10), min(len(t), i + 11)
            ctx.setdefault(ch, []).append('%s …%s…' % (rid, t[a0:b0].replace('\n', '⏎')))
    print('剩余超范围: %d 种 / %d 次' % (len(cnt), sum(cnt.values())))
    print()
    if only:
        for ch in only:
            print('=== %s ×%d' % (ch, cnt.get(ch, 0)))
            for c in ctx.get(ch, []):
                print('   %s' % c)
        return
    for i, (ch, n) in enumerate(cnt.most_common(top)):
        print('%-3s ×%-4d %s' % (ch, n, ctx[ch][0]))


if __name__ == '__main__':
    main()
