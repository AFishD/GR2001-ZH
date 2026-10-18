# -*- coding: utf-8 -*-
r"""lead_ft_logic.py — 查清 FT 记录表与 charset 的对齐关系: 哪些记录是引擎真需要的

输出:
  ① 544 条非空记录按 y 分带, 每带的 code 范围与是否在我们的 charset 里
  ② 记录 rect 里的墨量 + 该墨"像什么"(是否是我们的模板 / 是否是残留)
  ③ 结论: 哪些 rect 可以安全清空
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = HERE
while not os.path.isdir(os.path.join(REPO, '.git')) and REPO != os.path.dirname(REPO):
    REPO = os.path.dirname(REPO)
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import dump_font as D                                   # noqa: E402
import tcslib                                           # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'GR_ZH101.iso')
w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = cs['pair_of']
single_codes = {int(v) for v in cs['codes'].values()}
print('charset: 对偶字 %d ; 单字节码 %d 个 = %s'
      % (len(pair_of), len(single_codes), ' '.join('%02X' % c for c in sorted(single_codes))))

# ASCII: 0x20..0x7E 是否都在用?
import csv
textdir = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'text')
used_ascii = set()
for fn in os.listdir(textdir):
    if not fn.endswith('_text_short.csv') and not fn.endswith('_text_long.csv') \
       and not fn.endswith('_text_long_nowrap.csv'):
        continue
    with io.open(os.path.join(textdir, fn), encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            for ch in (row.get('text_edited') or ''):
                if ord(ch) < 0x80:
                    used_ascii.add(ord(ch))
print('文本里实际出现的 ASCII 字符 %d 个: %s' % (len(used_ascii), ''.join(sorted(chr(c) for c in used_ascii))))

# 记录表: 每个 face 一份 (idx → rect), code = idx + 0x20
print()
print('=' * 78)
print('① 非空记录按 y 分带 (取 large 面)')
print('=' * 78)
rec_large = None
for fname, _fld, rs in faces:
    if fname == 'large':
        rec_large = rs
print('large 面记录数 %d' % len(rec_large))
bands = {}
for idx, r in enumerate(rec_large):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 <= u0 or v1 <= v0:
        continue
    bands.setdefault(v0, []).append((idx + 0x20, u0, v0, u1, v1))
for y0 in sorted(bands):
    items = sorted(bands[y0])
    codes = [c for c, _a, _b, _d, _e in items]
    in_cs = sum(1 for c in codes if c in single_codes)
    tot = 0
    for c, u0, v0, u1, v1 in items:
        tot += int(ink[v0:v1, u0:u1].sum())
    print('  y=%-4d 记录 %2d 条  code %s..%s  在我们的 charset 里 %d 条  墨 %d px'
          % (y0, len(items), '%02X' % min(codes), '%02X' % max(codes), in_cs, tot))

print()
print('=' * 78)
print('② 逐条记录: code / rect / 墨 / 是否在我们的 charset')
print('=' * 78)
rows = []
for idx, r in enumerate(rec_large):
    _b0, _b1, u0, v0, u1, v1 = r
    if u1 <= u0 or v1 <= v0:
        continue
    code = idx + 0x20
    n = int(ink[v0:v1, u0:u1].sum())
    rows.append((code, u0, v0, u1, v1, n, code in single_codes))
need = [r for r in rows if r[6]]
unneed = [r for r in rows if not r[6]]
print('  需要的记录 (code 在 charset 里): %d 条, 墨 %d px' % (len(need), sum(r[5] for r in need)))
print('  不需要的记录 (code 不在 charset): %d 条, 墨 %d px' % (len(unneed), sum(r[5] for r in unneed)))
print()
print('  不需要但**有墨**的记录 (按墨量, 前 40):')
for code, u0, v0, u1, v1, n, _i in sorted(unneed, key=lambda r: -r[5])[:40]:
    if n == 0:
        continue
    print('     code=0x%02X rec[%3d]=(%4d,%3d,%4d,%4d) %3dpx' % (code, code - 0x20, u0, v0, u1, v1, n))
print()
print('  需要的记录里墨=0 的 (可能是空的):',
      ['%02X' % r[0] for r in need if r[5] == 0][:20])
