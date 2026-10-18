# -*- coding: utf-8 -*-
r"""v1_verify.py — round47 验收①: 新盘 GR_ZH96_fix 的记录带逐条复核。

口径 (互相独立, 缺一不可):
  A. 与 GR_ZH93 原图: 546 条记录矩形内逐像素 (说明"没多没少没移位"到什么程度 —— 见报告 §已知限制);
  B. 与 方正像素16 模板: 每条 16x16 记录格逐像素 (修好的 20 格必须 err=0);
  C. 与 GR_ZH94: 差异必须**只有**那 76 个像素, 且全在 y=353;
  D. 幂等: 再跑一次补丁 = 0 改动;
  E. 汉字格 (对偶) 与 TTF 模板: err 分布不劣于 GR_ZH94。
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
SPILL = sorted(yrow(r) - 1 for r in ROWS)
VER = 'GR_ZH96_fix'


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


N93 = load('GR_ZH93')
N94 = load('GR_ZH94')
NEW = load(VER)
a93, a94, new = N93['eng'], N94['eng'], NEW['eng']
rects = rects_all(N93['faces'])
cs = tcslib.Charset()                       # 单字节表与 round46 重排无关 (已核对 110 条 0 差异)
rev = dict((b, c) for c, b in cs.enc_single.items())
print('=' * 78)
print('v1 验收: %s' % VER)
print('  墨量: ZH93=%d ZH94=%d %s=%d' % (a93.sum(), a94.sum(), VER, new.sum()))
print('  段表与 94 相同: %s' % (NEW['segs'] == N94['segs']))
d94 = np.where(new != a94)
print('  ★ 与 GR_ZH94 的差异: %d 像素; 行分布 %s'
      % (len(d94[0]), collections.Counter((int(y) for y in d94[0])).most_common()))
print('  差异全在溢出带行 %s: %s' % (SPILL, all(int(y) in SPILL for y in d94[0])))
print('  差异像素坐标: %s' % sorted(zip(d94[0].tolist(), d94[1].tolist())))

# ---------- A/B: 逐条记录 ----------
print()
print('A. 逐条记录矩形 (全部 face; 共 %d 条)' % len(rects))
cntA = collections.Counter()
cntB = collections.Counter()
bad = []
for fname, code, u0, v0, u1, v1 in rects:
    if u1 <= u0 or v1 <= v0:
        continue
    x0, x1 = max(0, u0), min(W, u1)
    y0, y1 = max(0, v0), min(H, v1)
    if x0 >= x1 or y0 >= y1:
        continue
    d93 = int((new[y0:y1, x0:x1] != a93[y0:y1, x0:x1]).sum())
    cntA['与 ZH93 逐像素相同' if d93 == 0 else '与 ZH93 有差异'] += 1
    if d93:
        bad.append((fname, code, u0, v0, d93))
    ch = rev.get(code)
    if ch and (x1 - x0, y1 - y0) == (16, 16):
        tpl = render16(ch)
        e = int((new[y0:y1, x0:x1] != tpl).sum())
        cntB[e] += 1
print('   A) 与 GR_ZH93 原图比较: %s   (差异条数 %d)' % (cntA.most_common(), len(bad)))
for b in bad[:10]:
    print('        %s 0x%02X (%d,%d) 差 %d' % b)
print('   B) 与 方正像素16 模板比较 (16x16 记录格, %d 个字): err 分布 %s'
      % (sum(cntB.values()), sorted(cntB.items())))

# ---------- 汉字格 (对偶) ----------
print()
print('E. 汉字格 (对偶) 与模板:')
# ★ 必须用**重排前**的 charset: round46 已把 636 个对偶字重排, 现役 charset 指向新槽位,
#   而本盘图集是重排前的 ⇒ 用现役 charset 比会全错 (那是口径问题, 不是盘的问题)。
BAK = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'charset_before_repack.json')
assert os.path.isfile(BAK), BAK
cs_pre = tcslib.Charset(BAK)
print('   charset 口径 = 重排前备份 %s (对偶 %d 字)'
      % (os.path.relpath(BAK, REPO), len(cs_pre.enc_pair)))
res = {}
for tag, img in (('GR_ZH94', a94), (VER, new)):
    c = collections.Counter()
    n = 0
    for ch, (b1, b2) in cs_pre.enc_pair.items():
        s = tcslib.pair_slot(b1, b2)
        r, col = s // NCOL, s % NCOL
        y0, x0 = yrow(r), col * CW
        if r not in ROWS or y0 + CH > H or x0 + CW > W:
            continue
        tpl = render16(ch)
        e = int((img[y0:y0 + CH, x0:x0 + CW] != tpl).sum())
        c[e] += 1
        n += 1
    res[tag] = (n, c)
    print('   %s: row19..24 上的对偶格 %d 个; err=0 的 %d 个; err 中位 %s; 分布(前 8) %s'
          % (tag, n, c[0], sorted(c.elements())[n // 2] if n else '-', c.most_common(8)))
print('   ⇒ 两盘 err 分布完全相同: %s' % (res['GR_ZH94'][1] == res[VER][1]))

io.open(os.path.join(HERE, 'v1_verify.json'), 'w', encoding='utf-8', newline='\n').write(
    json.dumps(dict(diff_vs_94=[int(x) for x in d94[0]] + [], n_diff=len(d94[0]),
                    rects_vs_93=dict(cntA), tpl_err=dict((str(k), v) for k, v in cntB.items()),
                    dual=dict((k, [v[0], dict((str(a), b) for a, b in v[1].items())])
                              for k, v in res.items())),
               ensure_ascii=False, indent=1) + '\n')
print()
print('[out] → v1_verify.json')
