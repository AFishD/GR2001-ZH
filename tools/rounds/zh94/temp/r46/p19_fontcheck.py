# -*- coding: utf-8 -*-
r"""p19_fontcheck.py — 从版本 font/ 的 summary.json 里读出自查要点 (ZH94 vs ZH95)。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
for ver in ('GR_ZH94', 'GR_ZH95'):
    p = os.path.join(REPO, 'work', 'builds', ver, 'font', ver + '_font_summary.json')
    if not os.path.isfile(p):
        print('== %s: 没有 font summary ==' % ver)
        continue
    j = json.load(io.open(p, encoding='utf-8'))
    print('=' * 74)
    print('== %s ==' % ver)
    sc = j.get('grid_selfcheck') or {}
    print('  自查: %s' % (sc.get('note') or sc))
    print('  grid_selfcheck 不一致数 = %s ; 对偶字有字形 = %s / %s'
          % (sc.get('mismatched'), sc.get('pair_with_glyph'), sc.get('pair_total')))
    ga = j.get('grid_row_alignment') or {}
    bad = dict((k, v) for k, v in ga.items() if v not in (0, None)) if isinstance(ga, dict) else ga
    print('  grid_row_alignment 非 0 项: %s' % (bad or '无 (全 0 ✓)'))
    c = j.get('counts') or {}
    print('  字符 %s (缺字形 %s)' % (c.get('charset_rows'), c.get('missing_glyph')))
    P = (j.get('capacity') or {}).get('pair') or {}
    print('  容量 %s / 已用 %s / 空槽 %s' % (P.get('capacity'), P.get('used'), P.get('free')))
    print('  现在就能直接放新字 = %s ; 最严格口径 = %s'
          % (P.get('vacuum_usable'), P.get('strict_window_free')))
    print('  vacuum 按行: %s' % P.get('vacuum_rows'))
    A = j.get('atlas') or {}
    print('  图集墨点 %s / %s texel (%s%%)' % (A.get('ink_texels'), A.get('texels'),
                                              A.get('ink_ratio')))
    ms = j.get('missing_glyph_chars')
    print('  缺字形清单: %r' % (ms,))
