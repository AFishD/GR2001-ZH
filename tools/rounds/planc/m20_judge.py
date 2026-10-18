# -*- coding: utf-8 -*-
r"""m20_judge.py — 判决: 单字节与对偶两类字, 字形到底在哪个坐标系?

单字节 (111): (a) 记录框 (u0,v0)  (b) (u0+576)%1024, v0+1
对偶  (1300): (a) 引擎格 (16*C, yrow)  (b) PHI 格 (16*((C+PHI)%64), yrow)
用 方正像素16.ttf 16px 模板, 数 mismatch (0 = 完美)。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
import numpy as np                                     # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
W, H, CW, CH = 1024, 512, 16, 16
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return 2 + 16 * (r + (3 if r >= 12 else 0))


iso = tcslib.Iso(BASE)
ft_e = pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
    elif e['name'] == 'FONT.RES':
        ft_e = e
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
iso.close()
_he, faces = tcslib.parse_ft_faces(ft_blob)
RECS = faces[1][2]
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        PX = off
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
INK = (A == 0)

js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
singles = {ch: int(v) for ch, v in js['codes'].items()}
fnt = ImageFont.truetype(FZ, 16)


def render(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    return np.asarray(img)[8:24, 8:24] < 128


def mm(t, x, y):
    if x < 0 or y < 0 or x + CW > W or y + CH > H:
        return 10 ** 6
    return int((INK[y:y + CH, x:x + CW] != t).sum())


print('== 单字节 111: 记录框 vs 记录+576 ==')
a = b = 0
na = nb_ = 0
detail = []
for ch, code in sorted(singles.items(), key=lambda kv: kv[1]):
    idx = code - 0x20
    if idx < 0 or idx >= len(RECS):
        continue
    _b0, _b1, u0, v0, u1, v1 = RECS[idx]
    t = render(ch)
    if not t.any():
        continue
    m1 = mm(t, u0, v0)
    m2 = mm(t, (u0 + 576) % W, v0 + 1)
    na += 1
    a += (m1 == 0)
    b += (m2 == 0)
    if m1 != 0 and m2 != 0:
        detail.append((ch, code, u0, v0, m1, m2))
print('   记录框完美 %d/%d ; 记录+576 完美 %d/%d ; 都不完美 %d'
      % (a, na, b, na, len(detail)))
for d in detail[:15]:
    print('      %s 0x%02X rec=(%d,%d) m_rec=%d m_+576=%d' % d)

print()
print('== 对偶 1300: 引擎格 16*C vs PHI 格 ==')
ea = pb = eb = 0
tot = 0
rows = {}
for ch, (b0, b1) in pair_of.items():
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    t = render(ch)
    if not t.any():
        continue
    tot += 1
    m_eng = mm(t, 16 * C, yrow(R))
    m_phi = mm(t, 16 * ((C + PHI[R]) % 64), yrow(R))
    ea += (m_eng == 0)
    pb += (m_phi == 0)
    d = rows.setdefault(R, [0, 0, 0])
    d[0] += 1
    d[1] += (m_eng == 0)
    d[2] += (m_phi == 0)
print('   引擎格 (16*C) 完美 %d/%d ; PHI 格完美 %d/%d' % (ea, tot, pb, tot))
print('   行  n  引擎格=0  PHI格=0')
for R in sorted(rows):
    d = rows[R]
    print('   %2d %4d   %4d     %4d' % (R, d[0], d[1], d[2]))

print()
print('== 抽查: 的(0xAF) / 你(0xB0) / 米(AD D7) 三个位置的 mismatch ==')
for ch, code in (('的', 0xAF), ('你', 0xB0)):
    rec = RECS[code - 0x20]
    u0, v0 = rec[2], rec[3]
    t = render(ch)
    print('  %s 0x%02X rec=(%d,%d)  m_rec=%d  m_+576=%d  m_(16*C?)=n/a'
          % (ch, code, u0, v0, mm(t, u0, v0), mm(t, (u0 + 576) % W, v0 + 1)))
for ch in ('米', '延', '普'):
    if ch in pair_of:
        b0, b1 = pair_of[ch]
        s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
        R, C = s // 62, s % 62
        t = render(ch)
        print('  %s pair=%02X%02X slot=%d R=%d C=%d : m_16C@(%d,%d)=%d  m_PHI@(%d,%d)=%d'
              % (ch, b0, b1, s, R, C, 16 * C, yrow(R), mm(t, 16 * C, yrow(R)),
                 16 * ((C + PHI[R]) % 64), yrow(R), mm(t, 16 * ((C + PHI[R]) % 64), yrow(R))))
