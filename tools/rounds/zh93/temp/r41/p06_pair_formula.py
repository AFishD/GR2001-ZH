# -*- coding: utf-8 -*-
r"""p06_pair_formula.py — 独立复核「对偶码引擎格公式」(不依赖 lead 的 m20_judge)。

对 40 个对偶字 (跨行抽样, 含 x 回绕列与 row 19..24 新 lead 区), 用方正像素16 模板:
  · 在引擎格候选 (x = 16*((col+PHI[row])%64), y = yrow(row))      处数 mismatch
  · 在无相位候选 (x = 16*col) 与 legacy 候选 (x = 4+16*col) 处数 mismatch
  · 报告 0 误差命中数 ⇒ 与 docs/REPORT_plan_c_zh93.md 的 785/1297 互证
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                  # noqa: E402
from PIL import Image, ImageDraw, ImageFont                         # noqa: E402
import tcslib                                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
W, H, NCOL = 1024, 512, tcslib.NCOL
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2, 24: 0}


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def main():
    iso = tcslib.Iso(ISO)
    pak_e = None
    for i in range(24):
        e = iso.img_entry(tcslib.MENU_LBA, i)
        if e['name'] == 'COMMON.PAK':
            pak_e = e
            break
    pak = iso.read(pak_e['iso_off'], pak_e['stored'])
    iso.close()
    _nm, psm, w, h, clut, px_size, PX = [r for r in tcslib.parse_pak_records(pak)
                                         if r[0] == 'new_font_revised'][0]
    nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    INK = (A == 0)

    js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}

    fnt = ImageFont.truetype(FZ, 16)
    tcache = {}

    def render(ch):
        if ch in tcache:
            return tcache[ch]
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        tcache[ch] = win if win.any() else None
        return tcache[ch]

    def mm(tpl, x, y):
        if x < 0 or y < 0 or x + 16 > W or y + 16 > H:
            return 999
        return int((INK[y:y + 16, x:x + 16] != tpl).sum())

    # 抽样: 每个出现的 row 取前 2 个 (按 slot 序) + 所有 x 回绕的列各取 1 + row 24
    picked = []
    byrow = {}
    for ch, (b1, b2) in sorted(pair_of.items(), key=lambda kv: kv[1]):
        s = (b1 - tcslib.LEAD_LO) * 94 + (b2 - tcslib.LEAD_LO)
        r, c = s // NCOL, s % NCOL
        byrow.setdefault(r, []).append((ch, s, r, c))
    for r in sorted(byrow):
        rows = byrow[r]
        picked.extend(rows[:2])
        wrap = [t for t in rows if t[3] + PHI[r] >= 64]
        if wrap:
            picked.append(wrap[-1])
    seen, uniq = set(), []
    for t in picked:
        if t[1] not in seen:
            seen.add(t[1])
            uniq.append(t)

    print('抽样 %d 个对偶字 (跨 %d 行)' % (len(uniq), len(byrow)))
    print('%-4s %-4s %-3s %-3s %-5s | %-22s %-8s | %-22s %-8s | %-22s %-8s'
          % ('char', 'slot', 'row', 'col', 'wrap', '引擎格(PHI)', 'mismatch',
             '无相位 16*col', 'mismatch', 'legacy 4+16c', 'mismatch'))
    stat = dict(eng0=0, noph0=0, leg0=0, n=0, eng_le1=0)
    for ch, s, r, c in uniq:
        tpl = render(ch)
        if tpl is None:
            continue
        ph = PHI[r]
        ex = (16 * ((c + ph) % 64), yrow(r))
        nx = (16 * c, yrow(r))
        lx = (4 + 16 * c, yrow(r))
        me, mn, ml = mm(tpl, *ex), mm(tpl, *nx), mm(tpl, *lx)
        stat['n'] += 1
        stat['eng0'] += (me == 0)
        stat['eng_le1'] += (me <= 1)
        stat['noph0'] += (mn == 0)
        stat['leg0'] += (ml == 0)
        print('%-4s %-4d %-3d %-3d %-5s | (%4d,%3d) %-14s %-8d | (%4d,%3d) %-14s %-8d | (%4d,%3d) %-14s %-8d'
              % (ch, s, r, c, 'Y' if c + ph >= 64 else '', ex[0], ex[1], '', me,
                 nx[0], nx[1], '', mn, lx[0], lx[1], '', ml))
    print('\n== 汇总 (%d 个字) ==' % stat['n'])
    print('  引擎式 x=16*((col+PHI[row])%%64) : mismatch=0 → %d 个 ; mismatch<=1 → %d 个'
          % (stat['eng0'], stat['eng_le1']))
    print('  无相位 x=16*col                  : mismatch=0 → %d 个' % stat['noph0'])
    print('  legacy x=4+16*col                : mismatch=0 → %d 个' % stat['leg0'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
