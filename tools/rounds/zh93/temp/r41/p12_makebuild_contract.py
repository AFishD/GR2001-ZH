# -*- coding: utf-8 -*-
r"""p12_makebuild_contract.py — 冒烟: make_build.make_font_dump() 的接口契约没被改坏。

(只写 work/builds/GR_ZH93/temp/r41/ 下的临时目录; 不碰任何真实构筑产物。)
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import make_build                                                   # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
OUT = os.path.join(HERE, 'mkb_smoke')

info = make_build.make_font_dump(ISO, OUT, 'GR_ZH93')
print('\n== make_font_dump 返回的 build_info 片段 ==')
for k in sorted(info):
    v = info[k]
    print('  %-22s = %s' % (k, (str(v)[:110] + '…') if len(str(v)) > 110 else v))
need = ['dir', 'generated', 'deterministic', 'atlas_png', 'ft_csv', 'charset_csv',
        'summary_json', 'atlas', 'faces', 'ft_records', 'chars', 'by_kind',
        'has_glyph', 'missing_glyph', 'missing_glyph_chars', 'ft_records_with_ink',
        'ft_res_sha256']
miss = [k for k in need if k not in info]
print('\n契约字段缺失: %s' % (miss if miss else '无 ✓'))
sys.exit(1 if miss else 0)
