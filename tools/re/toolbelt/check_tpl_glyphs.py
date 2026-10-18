# -*- coding: utf-8 -*-
r"""check_tpl_glyphs.py — 查"模板字体"方正像素16.ttf 里是否有这些字
用途: 判定体检工具对 △ / 嘚 等的"与模板比对"是否属于假警报
"""
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from fontTools.ttLib import TTFont  # noqa: E402

TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
CHECKS = ['△', '▲', '✕', '✗', '键', '练', '用', '击', '嘚', '一', '二', '十', '的']
f = TTFont(TTF, fontNumber=0, lazy=True)
cmap = f.getBestCmap()
print('模板字体: %s' % os.path.basename(TTF))
print('cmap 条目数: %d' % len(cmap))
print()
missing = []
for ch in CHECKS:
    cp = ord(ch)
    has = cp in cmap
    if not has and ch not in ('嘚',):
        missing.append(ch)
    print('  %s U+%04X  %s' % (ch, cp, ('✓ 有' if has else '✗ **没有**')))
print()
print('⇒ 结论:')
for ch in ('△',):
    if ord(ch) not in cmap:
        print('  ★ 模板里**没有**「%s」⇒ 体检工具对它的"与模板比对"必然是**假警报** ✗' % ch)
        print('    ⇒ 应把它（以及「嘚」这类兜底/手绘字形）放进**豁免名单** ✓')
    else:
        print('  模板里**有**「%s」⇒ 比对有效，差异需真修 ✓' % ch)
