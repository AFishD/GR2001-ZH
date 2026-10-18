# -*- coding: utf-8 -*-
r"""p11_legacy_vs_engine.py — 每张盘上「legacy 格 vs 引擎格」对 1319 个对偶字的判定对比。

用途: 量化「把预检口径从 legacy 换成引擎式」在**每张可能当 --src 的盘**上各有多少差别。
"""
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISOS = ['GR_EN_ORIG', 'GR_ZH91', 'GR_ZH92', 'GR_ZH93']
NAMES = {'GR_EN_ORIG': '英文原盘(对照)', 'GR_ZH91': '中文旧版', 'GR_ZH92': '中文旧版',
         'GR_ZH93': '现役盘'}


def main():
    cs = tcslib.Charset()
    pairs = list(cs.enc_pair.items())
    print('%-12s %-14s %8s %8s %8s' % ('盘', '说明', '引擎格空', 'legacy空', '两者都空'))
    for name in ISOS:
        p = os.path.join(REPO, 'work', 'builds', name, name + '.iso')
        if not os.path.isfile(p):
            continue
        iso = tcslib.Iso(p)
        try:
            c = tcslib.GlyphCache(cs, iso)
            if not c.font_ok:
                print('%-12s 字库未装载' % name)
                continue
            cnt = Counter()
            legacy_only, engine_only = [], []
            for ch, (b1, b2) in pairs:
                s = tcslib.pair_slot(b1, b2)
                ex, ey = tcslib.atlas_cell_xy_engine(s)
                lx, ly = tcslib.atlas_cell_xy(s)
                e = c.cell_ink(ex, ey) <= 0
                l = c.cell_ink(lx, ly) <= 0
                cnt['eng'] += e
                cnt['leg'] += l
                cnt['both'] += (e and l)
                if l and not e:
                    legacy_only.append(ch)
                if e and not l:
                    engine_only.append(ch)
            print('%-12s %-14s %8d %8d %8d   | legacy 说缺但引擎有: %d 个%s ; '
                  '引擎说缺但 legacy 有: %d 个%s'
                  % (name, NAMES[name], cnt['eng'], cnt['leg'], cnt['both'],
                     len(legacy_only), (''.join(legacy_only[:12]) if legacy_only else ''),
                     len(engine_only), (''.join(engine_only[:12]) if engine_only else '')))
        finally:
            iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
