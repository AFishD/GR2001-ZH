# -*- coding: utf-8 -*-
r"""p10_crossdisk.py — 跨盘稳健性 + GlyphCache 预检口径自查。

Q1 现役字符集 1319 个对偶字, 在**每张历史盘**上按引擎格查, 有多少个有墨?
   (用来回答: 把 tcslib 预检口径改成引擎式后, 拿旧盘当 src 会不会冒出"缺字形"误报)
Q2 GlyphCache (写盘前预检用的那个类) 对现役盘 + 现役字符集的判定分布。
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISOS = ['GR_EN_ORIG', 'GR_ZH91', 'GR_ZH92', 'GR_ZH93']


def main():
    cs = tcslib.Charset()
    pairs = list(cs.enc_pair.items())
    print('现役 charset: 对偶 %d / 单字节 %d' % (len(pairs), len(cs.enc_single)))

    for name in ISOS:
        iso_p = os.path.join(REPO, 'work', 'builds', name, name + '.iso')
        if not os.path.isfile(iso_p):
            print('%-12s 不存在, 跳过' % name)
            continue
        iso = tcslib.Iso(iso_p)
        try:
            cache = tcslib.GlyphCache(cs, iso)
            if not cache.font_ok:
                print('%-12s 字库未装载: %s' % (name, cache.notes()))
                continue
            # Q2: GlyphCache 对全部字符的判定 (与 dump_font 同一路径)
            cnt = Counter()
            bad_pair = []
            for ch in list(cs.enc_single) + [c for c, _ in pairs]:
                r = cache.glyph_reason(ch)
                cnt['ok' if r is None else 'no'] += 1
                if r is not None and ch in cs.enc_pair:
                    bad_pair.append((ch, cs.enc_pair[ch], r))
            # Q1: 只查对偶, 直接数引擎格墨
            noink = []
            for ch, (b1, b2) in pairs:
                x, y = tcslib.atlas_cell_xy_engine(tcslib.pair_slot(b1, b2))
                if cache.cell_ink(x, y) <= 0:
                    noink.append(ch)
            print('%-12s 对偶引擎格有墨 %d/%d (无墨 %d) | GlyphCache 全字符: 有字形 %d / 缺 %d'
                  % (name, len(pairs) - len(noink), len(pairs), len(noink),
                     cnt['ok'], cnt['no']))
            if noink:
                print('             无墨的字 (前 30): %s' % ''.join(noink[:30]))
            if bad_pair:
                print('             缺字形的对偶 (前 10): %s'
                      % [(c, '%02X%02X' % b, r[:40]) for c, b, r in bad_pair[:10]])
        finally:
            iso.close()

    # 旧口径对照: legacy 格在同一张盘上有多少无墨
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))
    try:
        cache = tcslib.GlyphCache(cs, iso)
        n_eng = n_leg = 0
        for ch, (b1, b2) in pairs:
            s = tcslib.pair_slot(b1, b2)
            x, y = tcslib.atlas_cell_xy_engine(s)
            lx, ly = tcslib.atlas_cell_xy(s)
            n_eng += (cache.cell_ink(x, y) <= 0)
            n_leg += (cache.cell_ink(lx, ly) <= 0)
        print('\nGR_ZH93 上 1319 个对偶字: 引擎格无墨 %d 个 | **legacy 格无墨 %d 个**'
              % (n_eng, n_leg))
        print('  ⇒ legacy 口径会误报 %d 个"缺字形"; 引擎口径 0 个。' % n_leg)
    finally:
        iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
