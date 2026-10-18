# -*- coding: utf-8 -*-
r"""probe_chars_r63.py — 候选改动逐字体检 (字符集编码 + 盘上字形)。

用法: python probe_chars_r63.py "原文→新文" "原文→新文" ...
无参数时用内置候选表。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T                                                    # noqa: E402
import inject_text_csv as inj                                         # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'GR_ZH109.iso')
CAND = [
    ('国会最高勋章', '国会荣誉勋章'),          # Congressional Medal of Honor
    ('战功星章', '铜星勋章'),                  # Bronze Star
    ('战伤勋章', '紫心勋章'),                  # Purple Heart
    ('步兵战斗章 (CIB)', '步兵战斗徽章 (CIB)'),  # Combat Infantry Badge
    ('伊布拉伊姆', '易卜拉欣'),                # S. Ibrahim
    ('拉默雷斯', '拉米雷斯'),                  # H. Ramirez
    ('高登', '戈登'),                          # B. Gordon
    ('亚各布斯', '雅各布斯'),                  # W. Jacobs
    ('科汉', '科恩'),                          # L. Cohen
    ('海利', '海尔'),                          # J. Haile
    ('极限危机', '恐惧的总和'),                # The Sum of All Fears
    ('战役勋带', '战役勋表'),                  # Campaign Ribbons
]


def main():
    args = []
    for a in sys.argv[1:]:
        if '→' in a:
            o, n = a.split('→', 1)
        elif '->' in a:
            o, n = a.split('->', 1)
        else:
            o = n = a
        args.append((o, n))
    for (old, new) in (args or CAND):
        iso = T.Iso(ISO)
        cs = T.Charset()
        guard = T.GlyphCache(cs, iso)
        try:
            ob = cs.encode_strict(old)
            ob_ok = True
        except T.CharsetError as e:
            ob, ob_ok = b'', str(e)
        try:
            nb = cs.encode_strict(new)
            nb_ok = True
        except T.CharsetError as e:
            nb, nb_ok = b'', str(e)
        chk = guard.check_text(new) if nb_ok else []
        bad = [c for c in chk if c['kind'] not in inj.WARN_KINDS]
        print('%-16s → %-20s  %2d→%2d B (%+d)  %s'
              % (old, new, len(ob), len(nb), len(nb) - len(ob),
                 '编码OK' if (ob_ok and nb_ok) else '★编码失败'))
        if not ob_ok:
            print('     原文编码失败: %s' % ob)
        if not nb_ok:
            print('     新文编码失败: %s' % nb)
        for c in chk:
            print('     [%s] %r U+%04X %s%s'
                  % (c['kind'], c['char'], c['cp'], c['reason'],
                     '' if c['kind'] in inj.WARN_KINDS else '  ←★缺字/阻断'))
        if bad:
            print('     ⇒ **会被预检拦下**: %s'
                  % ' '.join('%r(%s)' % (c['char'], c['kind']) for c in bad))
        else:
            print('     ⇒ 预检通过 (字形齐全)')
        iso.close()


if __name__ == '__main__':
    main()
