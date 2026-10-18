# -*- coding: utf-8 -*-
r"""m6_survey.py — 落点普查 (只读):

以 FIXED 基盘 (含 57 字修复写入) 的图集为准, 对**每一个当前未被 charset 占用的 pair slot**:
  ① 算它的"引擎格"(前代理实测公式) 与 tcslib 口径格 (4+16c), 各数 16x16 墨量;
  ② 与**全部活字形窗口**求交 (1300 对偶 + 111 单字节 + ASCII, 三个 face 的记录 + 实测采样点),
     得到"写入会破坏多少活字形像素";
  ③ 输出按破坏量排序的候选表。

只读: 不改任何文件 (除 stdout)。
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
import tcslib                                          # noqa: E402

BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93_prev', 'temp', 'exp', 'FIXED.iso')
CS = tcslib.CHARSET
W, H, CW, CH = 1024, 512, 16, 16
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36, 19: 2, 20: 2, 21: 2, 22: 2, 23: 2}
SINGLE_DX, SINGLE_DY = 576, 1

print('base = %s' % BASE)
print('exists:', os.path.exists(BASE))
if not os.path.exists(BASE):
    BASE = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'exp', 'FIXED.iso')
    print('fallback base = %s (exists %s)' % (BASE, os.path.exists(BASE)))


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
print('FIXED 图集 墨=%d' % int(INK.sum()))

js = json.load(open(CS, encoding='utf-8'))
pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
singles = {ch: int(v) for ch, v in js['codes'].items()}
used_slots = {(b0 - 0xA1) * 94 + (b1 - 0xA1) for (b0, b1) in pair_of.values()}
used_codes = set(singles.values())

# ---------- 活字形窗口 ----------
live = np.zeros((H, W), dtype=bool)          # 被"活字形"占用的像素掩码
live_owner = {}


def stamp(x, y, tag):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + CW), min(H, y + CH)
    if x0 >= x1 or y0 >= y1:
        return
    live[y0:y1, x0:x1] = True
    live_owner.setdefault(tag, 0)
    live_owner[tag] += 1


for ch, (b0, b1) in pair_of.items():
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    if R not in PHI:
        continue
    x = 16 * ((C + PHI[R]) % 64)
    y = yrow(R) + (1 if C + PHI[R] >= 64 else 0)
    stamp(x, y, 'pair %s slot=%d' % (ch, s))

n_ft = 0
for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(FACE[fname]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        c = code + 0x20
        # 记录矩形 (工具口径) + 实测采样点 (单字节路径)
        if INK[max(0, v0):v0 + CH, max(0, u0):u0 + CW].any():
            stamp(u0, v0, 'ft%s 0x%02X rec' % (fname, c))
            n_ft += 1
        sx, sy = (u0 + SINGLE_DX) % W, v0 + SINGLE_DY
        if INK[max(0, sy):sy + CH, max(0, sx):sx + CW].any():
            stamp(sx, sy, 'ft%s 0x%02X eng' % (fname, c))
print('活窗口: 对偶 %d + FT 记录 %d 条 (三面)' % (len(pair_of), n_ft))

# ---------- 候选 slot 普查 ----------
free_rows = {}
for s in range(0, 1786):
    if s in used_slots:
        continue
    R, C = s // 62, s % 62
    lead = 0xA1 + s // 94
    trail = 0xA1 + s % 94
    x_phi = 16 * ((C + PHI[R]) % 64) if R in PHI else None
    y_phi = yrow(R) if R in PHI else None
    x_tcs = 4 + CW * C
    y_tcs = yrow(R)
    if y_tcs + CH > H:
        continue
    ink_phi = int(INK[y_phi:y_phi + CH, x_phi:x_phi + CW].sum()) if x_phi is not None else -1
    ink_tcs = int(INK[y_tcs:y_tcs + CH, x_tcs:x_tcs + CW].sum())
    dmg_phi = int(live[y_phi:y_phi + CH, x_phi:x_phi + CW].sum()) if x_phi is not None else -1
    dmg_tcs = int(live[y_tcs:y_tcs + CH, x_tcs:x_tcs + CW].sum())
    free_rows.setdefault(R, []).append(
        dict(s=s, R=R, C=C, lead=lead, trail=trail, x_phi=x_phi, y=y_phi,
             ink_phi=ink_phi, ink_tcs=ink_tcs, dmg_phi=dmg_phi, dmg_tcs=dmg_tcs))

print()
print('== 空闲 slot 概览 (按行) ==')
print('  行  yrow  空闲数  引擎格墨量 分布(最小/中位/最大)  tcslib格墨量 分布')
for R in sorted(free_rows):
    v = free_rows[R]
    ip = sorted(d['ink_phi'] for d in v)
    it = sorted(d['ink_tcs'] for d in v)
    print('  %2d  %3d   %4d    %4d / %4d / %4d            %4d / %4d / %4d'
          % (R, yrow(R), len(v), ip[0], ip[len(ip) // 2], ip[-1],
             it[0], it[len(it) // 2], it[-1]))

print()
print('== 最干净候选 (引擎格墨量 + tcslib 格墨量 都小) ==')
cand = []
for R in sorted(free_rows):
    for d in free_rows[R]:
        if d['x_phi'] is None or d['ink_phi'] < 0:
            continue                    # 行相位未知 (行 >= 24) ⇒ 本普查不用
        score = max(d['ink_phi'], d['ink_tcs'])
        cand.append((score, d['ink_phi'], d['ink_tcs'], d['dmg_phi'], d['dmg_tcs'], d))
cand.sort(key=lambda t: (t[0], t[1] + t[2]))
print('  #  行  C   码位    引擎格(x,y)   墨phi 墨tcs 破坏phi 破坏tcs')
for i, (sc, ip, it, dp, dt, d) in enumerate(cand[:60]):
    print('  %2d  %2d %3d  %02X%02X  (%4d,%3d)  %5s %5d  %5s %5d'
          % (i, d['R'], d['C'], d['lead'], d['trail'],
             d['x_phi'] if d['x_phi'] is not None else -1, d['y'],
             ip, it, dp, dt))

print()
print('== 逐行: 引擎格墨量 == 0 的 slot 明细 ==')
for R in sorted(free_rows):
    z = [d for d in free_rows[R] if d['ink_phi'] == 0]
    if z:
        print('  行 %2d: %d 个 → %s' % (R, len(z),
                                    ' '.join('%02X%02X(%d)' % (d['lead'], d['trail'], d['ink_tcs'])
                                             for d in z[:24])))

print()
print('== 现役(修复盘)已写入的 22 个对偶槽 复查 ==')
for s, ch in js.get('_font_ext_zh93_fix', {}).get('pair_slots', []):
    R, C = s // 62, s % 62
    x = 16 * ((C + PHI[R]) % 64)
    y = yrow(R)
    print('  slot=%4d %s 引擎格=(%4d,%3d) 墨=%3d tcslib格=(%4d,%3d) 墨=%3d'
          % (s, ch, x, y, int(INK[y:y + CH, x:x + CW].sum()), 4 + 16 * C, y,
             int(INK[y:y + CH, 4 + 16 * C:4 + 16 * C + CW].sum())))
