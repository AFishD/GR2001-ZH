# -*- coding: utf-8 -*-
r"""p10_glyph.py — 用工程自己的 GlyphCache 逐字问: 这 7 个字在 ZH93/ZH94 上到底有没有字形?"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                          # noqa: E402

CHARS = '若纤终脆膛荐著'
for ver in ('GR_ZH93', 'GR_ZH94', 'GR_ZH95'):
    p = os.path.join(REPO, 'work', 'builds', ver, ver + '.iso')
    if not os.path.isfile(p):
        continue
    cs = tcslib.Charset()
    g = tcslib.GlyphCache(cs, tcslib.Iso(p))
    print('=== %s (font_ok=%s) notes=%s' % (ver, g.font_ok, g.notes()))
    for ch in CHARS:
        code = cs.enc_single.get(ch)
        print('    %s  单字节=0x%s  有字形=%s  %s'
              % (ch, ('%02X' % code) if code else '--', g.has_glyph(ch),
                 (g.glyph_reason(ch) or '')[:90]))
    print('    hash_before=%s' % g.has_glyph('终'))

# 旧口径 (flat) 对照: 直接把 7 个记录矩形在 flat 视图里的墨量列出来
import numpy as np                                     # noqa: E402
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import dump_font                                       # noqa: E402
f = dump_font.load_font(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso'))
a = f['atlas']
stride = a['w'] // 2
cont = a['pak'][a['px_off']:a['px_off'] + a['px_size']]
n = min(len(cont) // stride, a['h'])
arr = np.frombuffer(cont[:n * stride], dtype=np.uint8).reshape(n, stride)
flat = np.zeros((a['h'], a['w']), dtype=bool)
flat[:n, 0::2] = (arr & 0x0F) == 0
flat[:n, 1::2] = (arr >> 4) == 0
recs = [x for x in f['faces'] if x[0] == 'default'][0][2]
print()
print('GR_ZH94 flat 口径: 7 个记录矩形里有多少墨 (旧 GlyphCache 就是看这里 → 当年判"有字形")')
for code in (0x92, 0x9D, 0x9E, 0x9F, 0xA0, 0xAE, 0xFF):
    r = recs[code - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    print('   0x%02X rect=(%d,%d,%d,%d) flat 墨=%d'
          % (code, u0, v0, u1, v1, int(flat[v0:v1, u0:u1].sum())))
