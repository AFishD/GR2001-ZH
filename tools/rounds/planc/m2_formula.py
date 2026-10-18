# -*- coding: utf-8 -*-
r"""m2_formula.py — 用现役盘 GR_ZH92 的图集做**判决性**测量:
每个 pair 字的字形到底落在哪个 x?

三个候选:
  A) tcslib.atlas_cell_xy   : x = 4  + 16*C
  B) gen_font16.cellpos     : x = 20 + 16*C
  C) 前代理 b20 实测公式     : x = 16*((C + PHI[R]) % 64)

判据: 用 方正像素16.ttf 渲染 16x16 模板, 数 16x16 窗内 mismatch texel 数。
只读, 不改任何文件。
"""
import json
import os
import struct
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))

import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import tcslib                                          # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}

CH, CW = 16, 16
Y0_, SKIP_R, SKIP_N = 2, 12, 3


def yrow(r):
    return Y0_ + CH * (r + (SKIP_N if r >= SKIP_R else 0))


iso = tcslib.Iso(ISO)
pak_e = ft_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
    elif e['name'] == 'FONT.RES':
        ft_e = e
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
print('COMMON.PAK stored=%d' % pak_e['stored'])
ATLAS = None
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        ATLAS = (w, h, off)
W, H, PX = ATLAS
print('atlas %dx%d psm/px_off=0x%X' % (W, H, PX))
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
INK = (A == 0)
print('atlas ink texels=%d' % int(INK.sum()))

ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
iso.close()
_he, faces = tcslib.parse_ft_faces(ft_blob)
print('FT faces=%s' % [(f[0], len(f[2])) for f in faces])
FACES = {f[0]: f[2] for f in faces}

js = json.load(open(CS, encoding='utf-8'))
pair_of = js['pair_of']
singles = js['codes']

fnt = ImageFont.truetype(FZ, 16)


def render(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    win = a[8:24, 8:24] < 128
    return win


def mismatch(t, x, y):
    if x < 0 or y < 0 or x + CW > W or y + CH > H:
        return 10 ** 6
    win = INK[y:y + CH, x:x + CW]
    return int((win != t).sum())


print()
print('== 判决: 每个 pair 字在三个候选 x 上的 mismatch (0 = 完美) ==')
stats = {}
detail = {}
for ch, (b0, b1) in pair_of.items():
    slot = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = slot // 62, slot % 62
    if R not in PHI:
        continue
    y = yrow(R)
    t = render(ch)
    if not t.any():
        continue
    xA, xB = 4 + CW * C, 20 + CW * C
    xC = 16 * ((C + PHI[R]) % 64)
    mA, mB, mC = mismatch(t, xA, y), mismatch(t, xB, y), mismatch(t, xC, y)
    d = stats.setdefault(R, [0, 0, 0, 0, 0])
    d[0] += 1
    if mA == 0:
        d[1] += 1
    if mB == 0:
        d[2] += 1
    if mC == 0:
        d[3] += 1
    if min(mA, mB, mC) != 0:
        d[4] += 1
        detail.setdefault(R, []).append((ch, C, mA, mB, mC))
print('  R    n   A(4+16C)=0  B(20+16C)=0  C(phi公式)=0   三者都不为0')
for R in sorted(stats):
    d = stats[R]
    print('  %2d  %4d      %4d        %4d         %4d          %4d'
          % (R, d[0], d[1], d[2], d[3], d[4]))
tot = [sum(stats[R][i] for R in stats) for i in range(5)]
print('  合计 %4d      %4d        %4d         %4d          %4d' % tuple(tot))
for R in sorted(detail):
    print('    R=%d 不完美样本: %s' % (R, detail[R][:6]))

print()
print('== 单字节 111 个: FT 记录矩形 vs 记录+576 采样点, 哪个有墨 ==')
recs = FACES['default']
ok_rec = ok_shift = ok_both = neither = 0
for ch, code in sorted(singles.items(), key=lambda kv: kv[1]):
    idx = code - 0x20
    if idx < 0 or idx >= len(recs):
        continue
    _b0, _b1, u0, v0, u1, v1 = recs[idx]
    t = render(ch)
    if not t.any():
        continue
    m_rec = mismatch(t, u0, v0)
    m_sh = mismatch(t, (u0 + 576) % W, v0 + 1)
    ok_rec += m_rec == 0
    ok_shift += m_sh == 0
    ok_both += (m_rec == 0) or (m_sh == 0)
    neither += (m_rec != 0 and m_sh != 0)
print('  记录矩形 (u0,v0) 完美: %d ; (u0+576)%1024,v0+1 完美: %d ; 至少一个完美: %d ; 都非完美: %d'
      % (ok_rec, ok_shift, ok_both, neither))
print()
for ch, code in sorted(singles.items(), key=lambda kv: kv[1])[:8]:
    idx = code - 0x20
    r = recs[idx]
    print('   %s 0x%02X idx=%d rec=(%d,%d,%d,%d)' % (ch, code, idx, r[2], r[3], r[4], r[5]))
