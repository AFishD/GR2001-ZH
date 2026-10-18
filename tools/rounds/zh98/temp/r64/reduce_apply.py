# -*- coding: utf-8 -*-
r"""reduce_apply.py — 把 reduce_rules.py 的替换规则套用到 old/<id>.txt, 生成 new/<id>.txt

用法:
  python reduce_apply.py              # 只给**还没有** new/<id>.txt 的条目生成草稿
  python reduce_apply.py --ids SFXML:T0050 ...
  python reduce_apply.py --force      # 覆盖已有 new/<id>.txt (会丢手工修改! 慎用)
  python reduce_apply.py --stat       # 只统计每条规则命中多少次, 不写盘

规则应用: 先 PER[id] 再 GLOB; 每张表内部按**片段长度降序** (长词优先)。
只写 new/, 不动其它任何文件。
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

OLD = os.path.join(HERE, 'old')
NEW = os.path.join(HERE, 'new')
TGT = os.path.join(HERE, 'reduce_targets.json')


def srt(rules):
    return sorted(rules, key=lambda kv: -len(kv[0]))


def apply_rules(text, rules, stat=None):
    for a, b in srt(rules):
        n = text.count(a)
        if n:
            if stat is not None:
                stat[(a, b)] += n
            text = text.replace(a, b)
    return text


def main():
    args = sys.argv[1:]
    force = '--force' in args
    ids = []
    if '--ids' in args:
        i = args.index('--ids')
        ids = [a for a in args[i + 1:] if a.startswith('SFXML:')]
    d = json.load(io.open(TGT, encoding='utf-8'))
    if not ids:
        ids = sorted(d)
    stat = Counter()
    for rid in ids:
        src = os.path.join(OLD, rid.replace(':', '_') + '.txt')
        dst = os.path.join(NEW, rid.replace(':', '_') + '.txt')
        if os.path.exists(dst) and not force:
            print('skip %-14s (已有改写稿)' % rid)
            continue
        text = io.open(src, encoding='utf-8', newline='').read()
        text = apply_rules(text, R.PER.get(rid, []), stat)
        text = apply_rules(text, R.GLOB, stat)
        io.open(dst, 'w', encoding='utf-8', newline='').write(text)
        miss = L.missing_of(text)
        print('%-14s %5d→%5d 字符  剩余超范围 %2d 种 / %3d 次  %s'
              % (rid, len(d['%s' % rid]['text']), len(text), len(miss),
                 L.missing_count(text), ''.join(miss[:40])))
    if '--stat' in args:
        print('\n规则命中统计 (前 40):')
        for (a, b), n in stat.most_common(40):
            print('   %-14s → %-14s ×%d' % (a, b or '(删)', n))


if __name__ == '__main__':
    main()
