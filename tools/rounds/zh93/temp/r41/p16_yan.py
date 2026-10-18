# -*- coding: utf-8 -*-
r"""p16_yan.py — 复核 Lead 留的「延 U+5EF6 缺字形」问题: 是**真缺**还是**旧格位公式误报**?

对每张盘: 报 延 的 pair 码位、引擎格/legacy 格坐标、两处的墨量, 以及 GlyphCache 现在的判定。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISOS = ['GR_ZH91', 'GR_ZH92', 'GR_ZH93']
CH = '延'


def main():
    cs = tcslib.Charset()
    b1, b2 = cs.enc_pair[CH]
    s = tcslib.pair_slot(b1, b2)
    r, c = s // tcslib.NCOL, s % tcslib.NCOL
    ex, ey = tcslib.atlas_cell_xy_engine(s)
    lx, ly = tcslib.atlas_cell_xy(s)
    ph = tcslib.atlas_row_phase(r)
    print('%s U+%04X pair=%02X%02X slot=%d row=%d col=%d PHI=%d%s'
          % (CH, ord(CH), b1, b2, s, r, c, ph,
             ' (x 回绕 ⇒ y 低 1 行)' if c + ph >= tcslib.GRID_MOD else ''))
    print('  引擎格 = (%d,%d)   legacy 格 = (%d,%d)' % (ex, ey, lx, ly))
    print('  另外两个口径: 无相位 16*col = (%d,%d)' % (16 * c, ey))
    for name in ISOS:
        p = os.path.join(REPO, 'work', 'builds', name, name + '.iso')
        if not os.path.isfile(p):
            continue
        iso = tcslib.Iso(p)
        try:
            cache = tcslib.GlyphCache(cs, iso)
            if not cache.font_ok:
                print('  %-10s 字库未装载' % name)
                continue
            e = cache.cell_ink(ex, ey)
            l = cache.cell_ink(lx, ly)
            n = cache.cell_ink(16 * c, ey)
            reason = cache.glyph_reason(CH)
            print('  %-10s 引擎格墨=%-4d legacy 格墨=%-4d 无相位格墨=%-4d | GlyphCache: %s'
                  % (name, e, l, n, '有字形 ✓' if reason is None else reason))
        finally:
            iso.close()
    # 曾经的 5 个 dead pair 全查一遍
    print('\n== 曾经的 dead pair (现役盘, 引擎口径) ==')
    iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso'))
    try:
        cache = tcslib.GlyphCache(cs, iso)
        for ch in '延志普略米':
            if ch not in cs.enc_pair:
                print('  %s 不在 charset' % ch)
                continue
            s = tcslib.pair_slot(*cs.enc_pair[ch])
            ex, ey = tcslib.atlas_cell_xy_engine(s)
            lx, ly = tcslib.atlas_cell_xy(s)
            rr = cache.glyph_reason(ch)
            print('  %s pair=%02X%02X slot=%-4d 引擎格(%4d,%3d) 墨=%-4d legacy 墨=%-4d ⇒ %s'
                  % (ch, cs.enc_pair[ch][0], cs.enc_pair[ch][1], s, ex, ey,
                     cache.cell_ink(ex, ey), cache.cell_ink(lx, ly),
                     '有字形 ✓' if rr is None else rr))
    finally:
        iso.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
