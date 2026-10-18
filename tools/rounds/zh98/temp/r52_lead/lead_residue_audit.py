# -*- coding: utf-8 -*-
r"""lead_residue_audit.py — 精确审计: 图集里哪些墨**既不是活字形、也不在引擎真正采样的窗里**

与 round49 `font_residue.py` 的差别: 那里 FT 记录窗被**膨胀 ±(4,2)**(保守, 宁可少清),
本脚本同时给出三档口径, 好判断"膨胀窗保护了多少垃圾":

  A 档 严格: 墨 ∧ ¬(已用对偶格) ∧ ¬(FT 记录矩形**原样**)
  B 档 膨胀: 墨 ∧ ¬(已用对偶格) ∧ ¬(FT 记录矩形 ±(4,2))     ← round49 用的
  C 档 只算对偶格: 墨 ∧ ¬(已用对偶格)                        ← 最激进

输出: 逐团块清单(位置/大小/被哪条记录保护) + 标注图 + 放大图
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image

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
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH101', 'temp', 'r52')
os.makedirs(OUT, exist_ok=True)

w = D.load_font(ISO)
ad, faces = w['atlas'], w['faces']
W, H = ad['w'], ad['h']
g = np.frombuffer(D.atlas_gray(ad, view='engine'), dtype=np.uint8).reshape(H, W)
ink = g < 128
print('图集 %dx%d, 墨 %d' % (W, H, int(ink.sum())))

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = cs['pair_of']

# ── 已用对偶格 (引擎口径) ────────────────────────────────────────────
used = np.zeros((H, W), dtype=bool)
n_used = 0
for ch, (b1, b2) in pair_of.items():
    if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
        continue
    slot = tcslib.pair_slot(b1, b2)
    x, y = tcslib.atlas_cell_xy_engine_view(slot)
    if 0 <= x and 0 <= y and x + 16 <= W and y + 16 <= H:
        used[y:y + 16, x:x + 16] = True
        n_used += 1
print('已用对偶格 %d 个 (lead 合法)' % n_used)

# ── FT 记录矩形 (3 个 face 全部非空记录) ─────────────────────────────
rects = []
for fname, _fld, rs in faces:
    for idx, r in enumerate(rs):
        _b0, _b1, u0, v0, u1, v1 = r
        if u1 <= u0 or v1 <= v0:
            continue
        rects.append((fname, idx, u0, v0, u1, v1))
print('FT 非空记录 %d 条' % len(rects))


def mask_from_rects(pad_x, pad_y):
    m = np.zeros((H, W), dtype=bool)
    for _f, _i, u0, v0, u1, v1 in rects:
        x0 = max(0, u0 - pad_x); x1 = min(W, u1 + pad_x)
        y0 = max(0, v0 - pad_y); y1 = min(H, v1 + pad_y)
        m[y0:y1, x0:x1] = True
    return m


strict = mask_from_rects(0, 0)
infl = mask_from_rects(4, 2)

mA = ink & ~used & ~strict          # 严格口径下的残墨
mB = ink & ~used & ~infl            # round49 口径
mC = ink & ~used                    # 只扣对偶格
print()
print('残墨像素:  A档(严格) %d  |  B档(±4,2 膨胀) %d  |  C档(只扣对偶格) %d'
      % (int(mA.sum()), int(mB.sum()), int(mC.sum())))
print('  ⇒ 膨胀窗"保护"下来的墨: %d px (A−B)' % int((mA & ~mB).sum()))
print('  ⇒ 落在 FT 记录矩形**原样**之内、但不在对偶格里的墨: %d px' % int((mC & strict).sum()))


def blobs(mask, min_px=1):
    """连通域 (4 邻域) → [(x0,y0,x1,y1,px)]"""
    from collections import deque
    seen = np.zeros_like(mask, dtype=bool)
    out = []
    ys, xs = np.nonzero(mask)
    for sy, sx in zip(ys.tolist(), xs.tolist()):
        if seen[sy, sx]:
            continue
        q = deque([(sy, sx)]); seen[sy, sx] = True
        x0 = x1 = sx; y0 = y1 = sy; n = 0
        while q:
            y, x = q.popleft(); n += 1
            x0 = min(x0, x); x1 = max(x1, x); y0 = min(y0, y); y1 = max(y1, y)
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = y + dy, x + dx
                if 0 <= ny < H and 0 <= nx < W and mask[ny, nx] and not seen[ny, nx]:
                    seen[ny, nx] = True; q.append((ny, nx))
        if n >= min_px:
            out.append((x0, y0, x1, y1, n))
    return sorted(out, key=lambda b: -b[4])


def who_protects(x, y):
    """这条墨被哪些 FT 记录窗保护 (膨胀口径)"""
    hits = []
    for f, i, u0, v0, u1, v1 in rects:
        if (u0 - 4) <= x < (u1 + 4) and (v0 - 2) <= y < (v1 + 2):
            hits.append('%s rec[%d]=(%d,%d,%d,%d)' % (f, i, u0, v0, u1, v1))
    return hits


print()
print('=' * 78)
print('B 档(round49 口径)下"被保留"但 A 档认为是垃圾的团块 (前 30, 按大小)')
print('=' * 78)
only_infl = mA & ~mB
bs = blobs(only_infl)
print('团块数 %d, 合计 %d px' % (len(bs), int(only_infl.sum())))
for x0, y0, x1, y1, n in bs[:30]:
    prot = who_protects((x0 + x1) // 2, (y0 + y1) // 2)
    print('  (%4d,%3d)-(%4d,%3d) %3dpx  被保护: %s' % (x0, y0, x1, y1, n, '; '.join(prot[:2]) or '(无)'))

print()
print('=' * 78)
print('A 档(严格口径)下的残墨团块 (前 30)')
print('=' * 78)
bsA = blobs(mA)
print('团块数 %d, 合计 %d px' % (len(bsA), int(mA.sum())))
for x0, y0, x1, y1, n in bsA[:30]:
    print('  (%4d,%3d)-(%4d,%3d) %4dpx  %dx%d' % (x0, y0, x1, y1, n, x1 - x0 + 1, y1 - y0 + 1))

# ── 标注图 ───────────────────────────────────────────────────────────
rgb = np.zeros((H, W, 3), dtype=np.uint8)
rgb[...] = (255, 255, 255)
rgb[used] = (200, 225, 255)                     # 已用对偶格 = 淡蓝
rgb[strict & ~used] = (220, 255, 220)           # FT 记录矩形 = 淡绿
rgb[only_infl] = (255, 160, 160)                # 被膨胀窗保护(疑似垃圾) = 红
rgb[mB] = (255, 0, 0)                           # round49 认定的残墨 = 深红
rgb[ink & ~used & ~strict & ~infl] = (255, 0, 0)
im = Image.fromarray(rgb)
im.resize((W * 2, H * 2), Image.NEAREST).save(os.path.join(OUT, 'residue_audit_map.png'))
print()
print('→ %s (淡蓝=活字形 / 淡绿=FT记录窗 / 红=被膨胀窗保护的墨)' % os.path.relpath(
    os.path.join(OUT, 'residue_audit_map.png'), REPO))

# ── 用户指出的两处, 高倍裁图 ─────────────────────────────────────────
# ① 三角块 (先按团块最大者定位) ② 任/稳 右侧
crops = []
if bs:
    x0, y0, x1, y1, _n = max(bs, key=lambda b: b[4])
    crops.append(('tri', max(0, x0 - 48), max(0, y0 - 24), min(W, x1 + 48), min(H, y1 + 24)))
# 单字节带右端 (稳 在 (432,482))
crops.append(('band_right', 384, 466, 512, 512))
crops.append(('band_gap', 0, 440, 512, 512))
for tag, x0, y0, x1, y1 in crops:
    c = Image.fromarray(g[y0:y1, x0:x1])
    s = 6
    c = c.resize(((x1 - x0) * s, (y1 - y0) * s), Image.NEAREST)
    p = os.path.join(OUT, 'crop_%s.png' % tag)
    c.save(p)
    print('→ %s  (图集坐标 x%d..%d, y%d..%d, %dx 放大)' % (os.path.relpath(p, REPO), x0, x1, y0, y1, s))
