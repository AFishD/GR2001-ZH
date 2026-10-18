# -*- coding: utf-8 -*-
r"""m8_pick.py — 为 16 个缺字挑选落点 (lead 0xAE 空间), 并**归因**每个候选格里那点墨是谁的。

判据 (从紧到松):
  A 级: 引擎格 16x16 墨=0 且 tcslib 格 墨=0 且四周 2px 空白
  B 级: 引擎格墨 <= 8 且 与任何活字形窗口零交叠
  C 级: 与任何活字形窗口零交叠 (墨可以更多)
归因: 谁在这些像素上有窗口 (对偶 / FT 记录 / FT 引擎采样点)。
只读。
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
MISS = '虽螺衍衣裂誉贡轮迟造钢题额鼓（）'


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
FACE = {f[0]: f[2] for f in faces}
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
inv_pair = {}
for ch, (b0, b1) in pair_of.items():
    inv_pair[(b0 - 0xA1) * 94 + (b1 - 0xA1)] = ch

# ---- 活字形窗口 + 归因表 ----
OWN = np.full((H, W), '', dtype=object)
LIVE = np.zeros((H, W), dtype=bool)


def stamp(x, y, tag):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + CW), min(H, y + CH)
    if x0 >= x1 or y0 >= y1:
        return
    sub = OWN[y0:y1, x0:x1]
    for yy in range(sub.shape[0]):
        for xx in range(sub.shape[1]):
            if sub[yy, xx] == '':
                sub[yy, xx] = tag
    LIVE[y0:y1, x0:x1] = True


for ch, (b0, b1) in pair_of.items():
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    x = 16 * ((C + PHI[R]) % 64)
    y = yrow(R) + (1 if C + PHI[R] >= 64 else 0)
    stamp(x, y, 'pair %02X%02X %s' % (b0, b1, ch))

for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(FACE[fname]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        c = code + 0x20
        if INK[max(0, v0):v0 + CH, max(0, u0):u0 + CW].any():
            stamp(u0, v0, 'FT%s 0x%02X rec' % (fname, c))
        sx, sy = (u0 + 576) % W, v0 + 1
        if INK[max(0, sy):sy + CH, max(0, sx):sx + CW].any():
            stamp(sx, sy, 'FT%s 0x%02X eng' % (fname, c))
print('活字形窗口像素 %d / 图集墨 %d' % (int(LIVE.sum()), int(INK.sum())))
dead_ink = INK & ~LIVE
print('**不属于任何活窗口的墨 = %d** (这些是可安全覆盖的死墨)' % int(dead_ink.sum()))

# ---- 普查 lead 0xAE 空间 ----
print()
print('== lead 0xAE 空闲槽落点 (行 19..21) ==')
rows = []
for s in range(1222, 1316):
    if s in used:
        continue
    R, C = s // 62, s % 62
    x = 16 * ((C + PHI[R]) % 64)
    y = yrow(R)
    xt = 4 + 16 * C
    win = INK[y:y + CH, x:x + CW]
    live_win = LIVE[y:y + CH, x:x + CW]
    ink = int(win.sum())
    dmg = int((win & live_win).sum())
    win_t = INK[y:y + CH, xt:xt + CW]
    live_t = LIVE[y:y + CH, xt:xt + CW]
    ink_t = int(win_t.sum())
    dmg_t = int((win_t & live_t).sum())
    # 归因
    who = {}
    ys, xs = np.where(win)
    for yy, xx in zip(ys, xs):
        t = OWN[y + yy, x + xx]
        who[t] = who.get(t, 0) + 1
    na = 0
    for dy in (-2, -1, 0, 1):
        for dx in (-2, -1, 0, 1):
            pass
    around = INK[max(0, y - 2):y + CH + 2, max(0, x - 2):x + CW + 2].sum()
    rows.append(dict(s=s, R=R, C=C, x=x, y=y, xt=xt, ink=ink, dmg=dmg, ink_t=ink_t,
                     dmg_t=dmg_t, who=who, around=int(around)))
rows.sort(key=lambda d: (d['dmg'], d['ink']))
print(' slot  码位  行  C   引擎格       墨 破坏   tcs格        墨 破坏  周围墨  墨的主人')
for d in rows:
    print(' %4d  %02X%02X  %2d %3d  (%4d,%3d)  %3d %3d   (%4d,%3d)  %3d %3d   %4d   %s'
          % (d['s'], 0xA1 + d['s'] // 94, 0xA1 + d['s'] % 94, d['R'], d['C'], d['x'], d['y'],
             d['ink'], d['dmg'], d['xt'], d['y'], d['ink_t'], d['dmg_t'], d['around'],
             '; '.join('%s x%d' % (k, v) for k, v in sorted(d['who'].items(), key=lambda kv: -kv[1])[:3]) or '-'))

print()
print('== 推荐 16+1 落点 (破坏=0 优先, 再看墨量) ==')
best = [d for d in rows if d['dmg'] == 0 and d['dmg_t'] == 0]
print('  破坏(引擎格)=0 且 破坏(tcs格)=0 的候选: %d 个' % len(best))
for d in best[:22]:
    print('   %02X%02X slot=%d 行%d 引擎格(%4d,%3d) 墨%3d 周围%4d | %s'
          % (0xA1 + d['s'] // 94, 0xA1 + d['s'] % 94, d['s'], d['R'], d['x'], d['y'],
             d['ink'], d['around'],
             '; '.join('%s x%d' % (k, v) for k, v in sorted(d['who'].items(), key=lambda kv: -kv[1])[:3]) or '-'))
