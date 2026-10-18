# -*- coding: utf-8 -*-
r"""m13_strict.py — 严格落点普查:
写入框 (16x16) 必须与**每一个活采样窗**完全不相交 (不只是"不覆盖活墨") ——
因为即便活窗那里是空白, 我写进去的墨也会出现在那个字的渲染里。

活窗集合 = 1300 对偶窗 (实测公式) ∪ 三个 face 的 FT 记录框 ∪ 单字节引擎采样窗 (u0+576, v0+1)。
候选 = lead 0xAE 空闲槽 (引擎格 与 tcs 格 都要满足)。
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
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
CS = tcslib.CHARSET
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
for (nm, psm, w, h, clut, px, off) in tcslib.parse_pak_records(pak):
    if nm == 'new_font_revised':
        PX = off
nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
A = np.empty((H, W), dtype=np.uint8)
A[:, 0::2] = nb & 0x0F
A[:, 1::2] = (nb >> 4) & 0x0F
INK = (A == 0)

js = json.load(open(CS, encoding='utf-8'))
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
used = {(b0 - 0xA1) * 94 + (b1 - 0xA1) for (b0, b1) in pair_of.values()}

WIN = np.zeros((H, W), dtype=bool)                 # 活采样窗 (含空白)


def box(x, y, tag):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + CW), min(H, y + CH)
    if x0 < x1 and y0 < y1:
        WIN[y0:y1, x0:x1] = True


for ch, (b0, b1) in pair_of.items():
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    x = 16 * ((C + PHI[R]) % 64)
    y = yrow(R) + (1 if C + PHI[R] >= 64 else 0)
    box(x, y, 'pair')

n_ft = 0
for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(faces[[f[0] for f in faces].index(fname)][2]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        box(u0, v0, 'ft')
        box((u0 + 576) % W, v0 + 1, 'ft')
        n_ft += 1
print('活采样窗像素 = %d / %d' % (int(WIN.sum()), W * H))

print()
print('== lead 0xAE 空闲槽: 严格判据 (引擎格 + tcs 格 都与活窗不相交) ==')
ok, bad = [], 0
for s in range(1222, 1316):
    if s in used:
        continue
    R, C = s // 62, s % 62
    x, y = 16 * ((C + PHI[R]) % 64), yrow(R)
    xt = 4 + 16 * C
    yt = y
    e_w = int(WIN[y:y + CH, x:x + CW].sum())
    t_w = int(WIN[yt:yt + CH, xt:xt + CW].sum())
    ink = int(INK[y:y + CH, x:x + CW].sum())
    ink_t = int(INK[yt:yt + CH, xt:xt + CW].sum())
    if e_w == 0 and t_w == 0:
        ok.append(dict(s=s, R=R, C=C, x=x, y=y, xt=xt, ink=ink, ink_t=ink_t))
    else:
        bad += 1
print('  合格 %d 个 / 不合格 %d 个 (lead 0xAE 共 %d 空闲槽)'
      % (len(ok), bad, sum(1 for s in range(1222, 1316) if s not in used)))
ok.sort(key=lambda d: d['ink'] + d['ink_t'])
print('   slot  码位  行 C   引擎格       墨  tcs格        墨')
for d in ok:
    print('   %4d  %02X%02X  %2d %3d (%4d,%3d) %4d (%4d,%3d) %4d'
          % (d['s'], 0xA1 + d['s'] // 94, 0xA1 + d['s'] % 94, d['R'], d['C'],
             d['x'], d['y'], d['ink'], d['xt'], d['y'], d['ink_t']))

print()
print('== 其它 lead 空间的合格数 (参考) ==')
for L in range(0xA1, 0xB4):
    cnt = 0
    for s in range((L - 0xA1) * 94, (L - 0xA1) * 94 + 94):
        if s in used or s >= 1786:
            continue
        R, C = s // 62, s % 62
        if R not in PHI:
            continue
        x, y = 16 * ((C + PHI[R]) % 64), yrow(R)
        xt = 4 + 16 * C
        if y + CH > H or yrow(R) + CH > H:
            continue
        if (WIN[y:y + CH, x:x + CW].sum() == 0
                and WIN[y:y + CH, xt:xt + CW].sum() == 0):
            cnt += 1
    print('  lead 0x%02X: 严格合格 %d 个' % (L, cnt))
