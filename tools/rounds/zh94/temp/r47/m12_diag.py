# -*- coding: utf-8 -*-
r"""m12_diag.py — round47 ⑫: 逐条记录的**权威诊断**。

对每条记录矩形:
  · 码 → 字符 (charset) → 方正像素16 模板 (gen_font16 同法);
  · 比 现盘图 vs 模板, 把差异**按行**归类;
  · 标出差异是否只落在"上一代字形溢出带" S = {yrow(r)-1 : r ∈ 19..24} = {353,369,385,401,417,433}。
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from r47lib import REPO, W, H, NCOL, CW, CH, yrow, load, rects_all, default_rects  # noqa: E402
import numpy as np                                                                 # noqa: E402
import tcslib                                                                      # noqa: E402
from PIL import Image, ImageDraw, ImageFont                                        # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)
ROWS = list(range(19, 25))
SPILL = set(yrow(r) - 1 for r in ROWS)
print('溢出带行号 S = %s' % sorted(SPILL))


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


for ver in ('GR_ZH93', 'GR_ZH94'):
    A = load(ver)
    a = A['eng']
    faces = A['faces']
    cs = tcslib.Charset()
    # 码 → 字符 (3 个 face 共用同一张码表; 用 enc_single)
    rev = dict((b, c) for c, b in cs.enc_single.items())
    rects = rects_all(faces)
    uniq = sorted(set((u0, v0, u1, v1) for _f, _c, u0, v0, u1, v1 in rects))
    print()
    print('=' * 78)
    print('%s: %d 条记录 / %d 个不同矩形' % (ver, len(rects), len(uniq)))
    codes_of = collections.defaultdict(set)
    for fname, code, u0, v0, u1, v1 in rects:
        codes_of[(u0, v0, u1, v1)].add(code)
    n_tpl = n_clean = n_spill_only = n_other = 0
    bad = []
    for (u0, v0, u1, v1) in uniq:
        w, h = u1 - u0, v1 - v0
        if w != 16 or h != 16:
            continue
        cur = a[v0:v1, u0:u1]
        chs = set()
        for code in codes_of[(u0, v0, u1, v1)]:
            ch = rev.get(code)
            if ch:
                chs.add(ch)
        for ch in sorted(chs):
            tpl = render16(ch)
            n_tpl += 1
            d = (cur != tpl)
            n = int(d.sum())
            if not n:
                n_clean += 1
                continue
            ys = np.where(d.any(axis=1))[0]
            abs_rows = sorted(set(int(v0 + y) for y in ys))
            if all(r in SPILL for r in abs_rows):
                n_spill_only += 1
                bad.append(dict(kind='仅溢出带', ch=ch, u0=u0, v0=v0, n=n, rows=abs_rows,
                                px=[[int(v0 + y), int(u0 + x)] for y, x in zip(*np.where(d))]))
            else:
                n_other += 1
                bad.append(dict(kind='别处', ch=ch, u0=u0, v0=v0, n=n, rows=abs_rows,
                                px=[[int(v0 + y), int(u0 + x)] for y, x in zip(*np.where(d))][:40]))
    print('  16x16 记录矩形里能对模板的字: %d 个' % n_tpl)
    print('    · 与模板**逐像素相同**: %d' % n_clean)
    print('    · 差异**只在溢出带** (⇒ 上一代字形残留污染): %d' % n_spill_only)
    print('    · 差异**在别处** (需人工看): %d' % n_other)
    for b in bad:
        print('    [%s] %s (%d,%d) 差 %d px 行 %s'
              % (b['kind'], b['ch'], b['u0'], b['v0'], b['n'], b['rows']))
        if b['kind'] == '仅溢出带':
            print('         像素: %s' % b['px'])
    if ver == 'GR_ZH93':
        keep = bad
print()
print('=' * 78)
print('差异只在溢出带的全部像素 (ZH93 = ZH94, 因为该行两盘相同):')
allpx = sorted(set(tuple(p) for b in keep if b['kind'] == '仅溢出带' for p in b['px']))
print('  合计 %d 个像素, 按行: %s'
      % (len(allpx), collections.Counter(p[0] for p in allpx).most_common()))
print('  %s' % allpx)
io.open(os.path.join(HERE, 'm12_diag.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps([b for b in keep], ensure_ascii=False, indent=1) + '\n')
print('[out] → m12_diag.json')
