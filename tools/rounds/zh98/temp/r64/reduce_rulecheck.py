# -*- coding: utf-8 -*-
r"""reduce_rulecheck.py — 校验 reduce_rules.py 的**替换目标**是否全部在字库内

规则表里只要有一个"改后片段"含超范围字, 就等于把缺字从左边搬到了右边 ⇒ 必须机器校验,
不能靠眼睛。顺带检查: 规则表里有没有**重复的 key** (后面的会覆盖前面的, 容易踩坑)。
只读, 不写盘; 有问题退出码 1。
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import reduce_lib as L                                                # noqa: E402
import reduce_rules as R                                              # noqa: E402


def check_table(name, rules):
    """★ 链式校验: 一条规则的「改后片段」还要再过一遍**排在它后面**的规则 (短的/后应用的),
    最后仍含超范围字才算真错 —— 否则会误报 "琳迪·科恩→琳迪·科安" 这种靠后续 ('琳','林')
    补齐的链式规则。"""
    srt = sorted(rules, key=lambda kv: -len(kv[0]))
    bad, keys = [], Counter()
    for i, (a, b) in enumerate(srt):
        keys[a] += 1
        cur = b
        for a2, b2 in srt[i + 1:]:
            if a2 in cur:
                cur = cur.replace(a2, b2)
        miss = [c for c in cur if not L.encodable(c)]
        if miss:
            bad.append((a, b, ''.join(dict.fromkeys(miss))))
    dup = [k for k, v in keys.items() if v > 1]
    print('── %-22s %4d 条规则' % (name, len(rules)))
    for a, b, m in bad:
        print('   [!!] %r → %r   改后仍有超范围字: %s' % (a, b, m))
    if dup:
        print('   [提示] 重复 key: %s' % ' '.join(repr(d) for d in dup))
    return len(bad)


def main():
    n = check_table('NAME', R.NAME)
    n += check_table('GLOB_GENERAL', R.GLOB_GENERAL)
    for rid, rules in sorted(R.PER.items()):
        n += check_table('PER[%s]' % rid, rules)
    print('\n合计 %d 条规则的改后片段含超范围字' % n)
    return 1 if n else 0


if __name__ == '__main__':
    sys.exit(main())
