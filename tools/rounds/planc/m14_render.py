# -*- coding: utf-8 -*-
r"""m14_render.py — 用"盘上真的会渲染的码"重建活窗集合, 再严格普查落点。

活窗 = ① 全部 ASCII 码 (所有 face 的记录框 + 引擎采样点)
       ② 全部 111 个单字节码 (同上)
       ③ **盘上文本里真的出现过的** pair (按新 gate 语义解析盘上字节)
       ④ 修复盘新写入的 22 个 pair (它们在用户新译文里)
不活 = 其余对偶码 (闲置/死 pair) —— 它们在本盘上永远不会被绘制。
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
GATE = 0xAF                # 计划: lead 0xA1..0xAE


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
# 盘上文本 (与基盘同源; FIXED 未注文本, 故用现役 GR_ZH92 的容器做"用字"统计)
iso2 = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso'))
blobs = []
for (lba, idx) in ((tcslib.MENU_LBA, 25), (tcslib.MENU_LBA, tcslib.XML_IDX),
                   (tcslib.GR_LBA, 902)):
    e = iso2.img_entry(lba, idx)
    blobs.append(b''.join(s[0] for s in tcslib.lzo_subs(iso2.read(e['iso_off'], e['stored']))))
iso.close()
iso2.close()

used_pairs = set()
used_singles = set()
for b in blobs:
    i, n = 0, len(b)
    while i < n:
        v = b[i]
        if 0xA1 <= v < GATE and i + 1 < n and 0xA1 <= b[i + 1] <= 0xFE:
            used_pairs.add((v, b[i + 1]))
            i += 2
            continue
        if v >= 0x80:
            used_singles.add(v)
        i += 1
print('盘上文本用到的: pair %d 种, 单字节 %d 种 → %s'
      % (len(used_pairs), len(used_singles),
         ' '.join('%02X' % c for c in sorted(used_singles))))

_he, faces = tcslib.parse_ft_faces(ft_blob)
FACEI = {f[0]: i for i, f in enumerate(faces)}
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
inv_pair = {(b0, b1): ch for ch, (b0, b1) in pair_of.items()}
used_slots = {(b0 - 0xA1) * 94 + (b1 - 0xA1) for (b0, b1) in pair_of.values()}

WIN = np.zeros((H, W), dtype=bool)


def box(x, y):
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(W, x + CW), min(H, y + CH)
    if x0 < x1 and y0 < y1:
        WIN[y0:y1, x0:x1] = True


n_win = 0
for fname in ('large', 'default', 'huge'):
    for code, rec in enumerate(faces[FACEI[fname]][2]):
        _b0, _b1, u0, v0, u1, v1 = rec
        if u1 <= u0 or v1 <= v0:
            continue
        c = code + 0x20
        if c < 0x80 or c in used_singles or c in (0x92, 0xAE, 0xFF):
            box(u0, v0)
            box((u0 + 576) % W, v0 + 1)
            n_win += 1
print('ASCII/单字节 活窗 %d 条' % n_win)

nc = 0
for (b0, b1) in used_pairs:
    s = (b0 - 0xA1) * 94 + (b1 - 0xA1)
    R, C = s // 62, s % 62
    if R not in PHI:
        continue
    x = 16 * ((C + PHI[R]) % 64)
    y = yrow(R) + (1 if C + PHI[R] >= 64 else 0)
    box(x, y)
    nc += 1
print('文本里真用到的 pair 活窗 %d 条' % nc)

print()
print('== lead 0xAE 空闲槽: 严格判据 (与"真会渲染的"窗不相交) ==')
ok = []
for s in range(1222, 1316):
    if s in used_slots:
        continue
    R, C = s // 62, s % 62
    x, y = 16 * ((C + PHI[R]) % 64), yrow(R)
    xt = 4 + 16 * C
    e_w = int(WIN[y:y + CH, x:x + CW].sum())
    t_w = int(WIN[y:y + CH, xt:xt + CW].sum())
    ink = int(INK[y:y + CH, x:x + CW].sum())
    ink_t = int(INK[y:y + CH, xt:xt + CW].sum())
    if e_w == 0 and t_w == 0:
        ok.append((s, R, C, x, y, xt, ink, ink_t, e_w + t_w))
ok.sort(key=lambda t: t[6] + t[7])
print('  合格 %d 个' % len(ok))
print('   slot  码位  行 C   引擎格       墨  tcs格        墨')
for (s, R, C, x, y, xt, ink, ink_t, _w) in ok:
    print('   %4d  %02X%02X  %2d %3d (%4d,%3d) %4d (%4d,%3d) %4d'
          % (s, 0xA1 + s // 94, 0xA1 + s % 94, R, C, x, y, ink, xt, y, ink_t))
