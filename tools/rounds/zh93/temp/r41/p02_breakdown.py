# -*- coding: utf-8 -*-
r"""p02_breakdown.py — 把「空位 185」按多种候选判据拆开, 找出哪一种给出 (45, 140)。

候选判据 (对每个空位 slot):
  A engine_cell_ink == 0                     (有 PHI 的行)
  B engine 格 + 回绕补窗 (col+PHI>=64 时再看 y+1)  都空
  C engine cell 空 且 legacy cell 空
  D row24: 假设 PHI=2 时的 cell 墨
  E 活窗 (LIVE) 零交叠
输出每个判据下的 count, 并打印 row24 的 16 格细节。
"""
import json
import os
import sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
LEAD_LO, LEAD_HI = tcslib.LEAD_LO, tcslib.LEAD_HI
SLOTS = (LEAD_HI - LEAD_LO) * 94
NCOL, W, H = tcslib.NCOL, 1024, 512
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def main():
    iso = tcslib.Iso(ISO)
    ft_e = pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'FONT.RES':
            ft_e = e
        elif e['name'] == 'COMMON.PAK':
            pak_e = e
        if ft_e and pak_e:
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    ft_slot = iso.read(ft_e['iso_off'], ft_e['stored'])
    iso.close()
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(ft_slot))
    _he, faces = tcslib.parse_ft_faces(ft_blob)
    rec = [r for r in tcslib.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    _nm, psm, w, h, clut, px_size, PX = rec

    LONIB = bytes(i & 0xF for i in range(256))
    HINIB = bytes((i >> 4) & 0xF for i in range(256))
    A = []
    for y in range(h):
        rb = pak[PX + y * (w // 2): PX + y * (w // 2) + (w // 2)]
        A.append((rb.translate(LONIB), rb.translate(HINIB)))

    def ink(x, y, cw=16, ch=16):
        n = 0
        for yy in range(max(0, y), min(h, y + ch)):
            lo, hi = A[yy]
            for xx in range(max(0, x), min(w, x + cw)):
                if (lo[xx >> 1] if (xx & 1) == 0 else hi[xx >> 1]) == 0:
                    n += 1
        return n

    js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
    used = set()
    for b1, b2 in pair_of.values():
        used.add((b1 - LEAD_LO) * 94 + (b2 - LEAD_LO))
    free = [s for s in range(SLOTS) if s not in used]
    print('slot 容量 %d / 已用 %d / 空位 %d' % (SLOTS, len(used), len(free)))

    # ---------- row 24 细节 ----------
    print('\n== row 24 (slot 1488..1503, lead 0xB0 trail 0xEF..0xFE) yrow=%d ==' % yrow(24))
    for ph in (None, 0, 2, 6, 12, 18, 24, 30, 36):
        lab = 'no-PHI' if ph is None else 'PHI=%-2d' % ph
        if ph is None:
            # 直接扫 y=434 整行 16px 分块, 看哪几块空
            empt = [c for c in range(16) if ink(16 * c, 434) == 0]
            print('  %s: y=434 上 x=16*col(0..15) 空的列 = %s (%d 个)' % (lab, empt, len(empt)))
            continue
        empt = [c for c in range(16) if ink(16 * ((c + ph) % 64), 434) == 0]
        print('  %s: x=16*((col+%d)%%64) 空 = %d 个  %s' % (lab, ph, len(empt), empt))

    # ---------- 各判据 ----------
    def cln(ph_map, extra_y=False):
        out = []
        for s in free:
            r, c = s // NCOL, s % NCOL
            ph = ph_map.get(r)
            if ph is None:
                continue
            x = 16 * ((c + ph) % 64)
            y = yrow(r)
            if ink(x, y) == 0 and (not extra_y or ink(x, y + 1) == 0):
                out.append(s)
        return out

    cand = {}
    cand['A engine cell 空 (PHI 行)'] = cln(PHI)
    cand['B engine cell + y+1 都空'] = cln(PHI, True)
    cand['A+row24(PHI=2)'] = cln(PHI) + [s for s in free if s // NCOL == 24
                                         and ink(16 * ((s % NCOL + 2) % 64), 434) == 0]
    cand['A+row24(PHI=0)'] = cln(PHI) + [s for s in free if s // NCOL == 24 and ink(16 * (s % NCOL), 434) == 0]
    # C: engine 空 且 legacy 空
    cc = []
    for s in free:
        r, c = s // NCOL, s % NCOL
        ph = PHI.get(r)
        if ph is None:
            continue
        if ink(16 * ((c + ph) % 64), yrow(r)) == 0 and ink(tcslib.atlas_cell_xy(s)[0], yrow(r)) == 0:
            cc.append(s)
    cand['C engine 空 且 legacy 空'] = cc

    # E: 活窗零交叠 (engine 格 + 全部 FT 记录采样窗)
    LIVE = [[False] * W for _ in range(H)]

    def mark(x, y):
        for yy in range(max(0, y), min(H, y + 16)):
            row = LIVE[yy]
            for xx in range(max(0, x), min(W, x + 16)):
                row[xx] = True

    for ch, (b1, b2) in pair_of.items():
        s = (b1 - LEAD_LO) * 94 + (b2 - LEAD_LO)
        r, c = s // NCOL, s % NCOL
        ph = PHI.get(r)
        if ph is None:
            continue
        mark(16 * ((c + ph) % 64), yrow(r))
    for fname, fld, recs in faces:
        for (b0, b1r, u0, v0, u1, v1) in recs:
            if u1 <= u0 or v1 <= v0:
                continue
            mark(u0, v0)
            mark((u0 + 576) % W, v0 + 1)
            for rr, ph in PHI.items():
                if yrow(rr) == v0:
                    mark((u0 + 16 * ph) % W, v0 + 1)
    ee = []
    for s in free:
        r, c = s // NCOL, s % NCOL
        ph = PHI.get(r)
        if ph is None:
            continue
        x, y = 16 * ((c + ph) % 64), yrow(r)
        if y + 16 <= H and x + 16 <= W and not any(LIVE[yy][xx]
                                                  for yy in range(y, y + 16) for xx in range(x, x + 16)):
            ee.append(s)
    cand['E 活窗零交叠'] = ee

    print('\n== 候选判据下的「可直接用」数量 ==')
    for k, v in cand.items():
        print('  %-28s = %-4d  (需回收 %d)' % (k, len(v), len(free) - len(v)))
    print('  ★ 目标 (Lead 给的)          = 45    (需回收 140)')

    # ---------- 45 的搜索 ----------
    print('\n== 反查: 哪个「A 的子集」= 45 ==')
    A_ = cand['A engine cell 空 (PHI 行)']
    print('  A = %d 个, 按 row: %s' % (len(A_), sorted(Counter(s // NCOL for s in A_).items())))
    print('  A 的 slot: %s' % A_)
    dirty = [s for s in free if s not in A_ and s // NCOL != 24]
    print('  有墨空位 %d 个, 按 row: %s' % (len(dirty), sorted(Counter(s // NCOL for s in dirty).items())))
    # 看看 row24 各种 PHI 下空的数量
    for ph in range(64):
        n = sum(1 for c in range(16) if ink(16 * ((c + ph) % 64), 434) == 0)
        if n:
            print('    row24 PHI=%-2d → 空 %d 个' % (ph, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
