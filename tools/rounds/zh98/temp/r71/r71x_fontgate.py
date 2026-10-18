# -*- coding: utf-8 -*-
r"""r71x_fontgate.py — 门禁⑦: dump_font 缺字形 0 + 字符集/槽位状态 + 共享文件是否被改"""
import hashlib
import io
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
HERE = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

p = os.path.join(REPO, 'work', 'builds', 'GR_ZH113_B', 'font', 'GR_ZH113_B_font_summary.json')
d = json.load(io.open(p, encoding='utf-8'))
print('=== GR_ZH113_B 字库 dump ===')
print('  counts        :', json.dumps(d['counts'], ensure_ascii=False))
print('  missing_glyph : %d 个 %s' % (len(d['missing_glyph_chars']),
                                     '✓' if not d['missing_glyph_chars'] else d['missing_glyph_chars'][:20]))
print('  glyph_face_checked:', json.dumps(d.get('glyph_face_checked'), ensure_ascii=False)[:200])
print('  atlas ink     : %s / %s texel' % (d['atlas']['ink_texels'], d['atlas']['total_texels']))
print('  grid          : ncol=%(ncol)s cw=%(cw)s ch=%(ch)s y0=%(y0)s' % d['grid'])

print()
print('=== 共享文件 (charset JSON) 是否被本轮构筑改动 ===')
cs = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
h = hashlib.sha256(io.open(cs, 'rb').read()).hexdigest()
before = io.open(os.path.join(HERE, 'charset_sha_before.txt'), encoding='ascii').read().strip()
print('  构筑前 %s' % before)
print('  现在   %s' % h.upper())
print('  %s' % ('未改动 ✓' if h.upper() == before.upper() else '★ 变了 (font_compact stamp_charset)'))

print()
print('=== 与 GR_ZH113 的字库对比 ===')
a = json.load(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH113', 'font',
                                  'GR_ZH113_font_summary.json'), encoding='utf-8'))
print('  counts 113  :', json.dumps(a['counts'], ensure_ascii=False))
print('  atlas sha113: %s' % a['atlas']['pixel_sha256'][:16])
print('  atlas sha113B: %s  %s' % (d['atlas']['pixel_sha256'][:16],
                                  '相同 ✓' if a['atlas']['pixel_sha256'] == d['atlas']['pixel_sha256'] else '不同 ✗'))
print('  ft 记录数 113/113B: %d / %d' % (a['counts']['ft_records'], d['counts']['ft_records']))
