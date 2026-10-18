# -*- coding: utf-8 -*-
r"""glyph_avail.py — 查「嘚」U+561A 在哪些字体里有（决定怎么补这个缺字）"""
import glob
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from fontTools.ttLib import TTFont  # noqa: E402

TARGETS = [0x561A, 0x5F97, 0x7684, 0x5730]  # 嘚 / 得 / 的 / 地
NAMES = {0x561A: '嘚', 0x5F97: '得', 0x7684: '的', 0x5730: '地'}

pats = ['*.ttf', '*.otf', '*.ttc', '**/*.ttf', '**/*.otf']
found = set()
for p in pats:
    for f in glob.glob(os.path.join(REPO, 'third_party', 'fonts', p), recursive=True):
        found.add(f)
fonts = sorted(found)
print('third_party/fonts 下找到 %d 个字体文件' % len(fonts))
for f in fonts[:20]:
    try:
        t = TTFont(f, fontNumber=0, lazy=True)
        cmap = t.getBestCmap()
        have = [NAMES[c] for c in TARGETS if c in cmap]
        miss = [NAMES[c] for c in TARGETS if c not in cmap]
        print('  %-42s 有: %-14s 缺: %s' % (os.path.basename(f), ''.join(have) or '-', ''.join(miss) or '-'))
    except Exception as e:
        print('  %-42s 读取失败: %s' % (os.path.basename(f), str(e)[:60]))

# 顺带看系统字体里是否有可用替代（仅报告，不使用）
sysdir = os.path.join(os.environ.get('WINDIR', r'C:\Windows'), 'Fonts')
cands = ['msyh.ttc', 'simhei.ttf', 'simsun.ttc', 'Deng.ttf', 'msyhbd.ttc']
print()
print('系统字体（仅供参考，是否使用由你决定）:')
for c in cands:
    p = os.path.join(sysdir, c)
    if not os.path.exists(p):
        continue
    try:
        t = TTFont(p, fontNumber=0, lazy=True)
        cmap = t.getBestCmap()
        print('  %-16s 有嘚: %s' % (c, '✓' if 0x561A in cmap else '✗'))
    except Exception as e:
        print('  %-16s 读取失败 %s' % (c, str(e)[:50]))
