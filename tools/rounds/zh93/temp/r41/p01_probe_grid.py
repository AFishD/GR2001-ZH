# -*- coding: utf-8 -*-
r"""p01_probe_grid.py — round41 探针: 用现役盘实测「引擎格公式」的覆盖情况。

问题清单:
  Q1 1504 个 slot 的 row 分布; row 24 有多少 slot（PHI 表只到 23）
  Q2 1319 个已用 pair 的字形, 在「引擎格 x=16*((col+PHI[row])%64), y=yrow(row)」处有墨吗?
  Q3 x 回绕的格 (col+PHI>=64): y 用 yrow(row) 还是 yrow(row)+1 有墨?
  Q4 空位 185 个里, 引擎格真空(=0 墨)的有几个?
  Q5 legacy 口径 atlas_cell_xy (x=4+16c) 与引擎格不同的 slot 数
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
LEAD_LO = tcslib.LEAD_LO
LEAD_HI = tcslib.LEAD_HI
TRAIL_LO, TRAIL_HI = 0xA1, 0xFE
NCOL = tcslib.NCOL
W, H = 1024, 512
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2}
SLOTS = (LEAD_HI - LEAD_LO) * (TRAIL_HI - TRAIL_LO + 1)


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def slot_of(b1, b2):
    return (b1 - LEAD_LO) * 94 + (b2 - LEAD_LO)


def main():
    print('== p01 引擎格公式探针 ==')
    print('LEAD [0x%02X,0x%02X) TRAIL [0x%02X,0x%02X] ⇒ slot 容量 = %d'
          % (LEAD_LO, LEAD_HI, TRAIL_LO, TRAIL_HI, SLOTS))

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
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    _nm, psm, w, h, clut, px_size, PX = rec
    print('图集 %dx%d psm=0x%02X px_off=0x%X' % (w, h, psm, PX))

    # 位图: rowbytes 缓存 (byte -> (lo,hi) nibble 表)
    LONIB = bytes(i & 0xF for i in range(256))
    HINIB = bytes((i >> 4) & 0xF for i in range(256))
    rows = {}
    for y in range(h):
        rb = pak[PX + y * (w // 2): PX + y * (w // 2) + (w // 2)]
        rows[y] = (rb.translate(LONIB), rb.translate(HINIB))

    def inkat(x, y):
        cell = inkat_rect(x, y, 16, 16)
        return cell

    cache = {}

    def inkat_rect(x, y, cw, ch):
        k = (x, y, cw, ch)
        if k in cache:
            return cache[k]
        n = 0
        for yy in range(y, y + ch):
            if yy < 0 or yy >= h:
                continue
            lo, hi = rows[yy]
            for xx in range(x, x + cw):
                if xx < 0 or xx >= w:
                    continue
                if (lo[xx >> 1] if (xx & 1) == 0 else hi[xx >> 1]) == 0:
                    n += 1
        cache[k] = n
        return n

    # ── Q1 row 分布 ──
    from collections import Counter
    rowc = Counter(s // NCOL for s in range(SLOTS))
    print('\n[Q1] slot 的 row 分布: %s' % sorted(rowc.items()))
    print('     最大 row = %d (slot %d..%d)' % (max(rowc), max(rowc) * NCOL, SLOTS - 1))
    print('     PHI 表覆盖 row: %s' % sorted(PHI))
    print('     ⇒ row %d 有 %d 个 slot 没有 PHI 表项' % (24, rowc.get(24, 0)))
    print('     yrow(24) = %d (+16 = %d, 图集高 %d)' % (yrow(24), yrow(24) + 16, h))

    # ── 字符集 ──
    js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
    used = {}
    for ch, (b1, b2) in pair_of.items():
        used.setdefault(slot_of(b1, b2), []).append(ch)
    print('\n[charset] pair 数 %d (唯一 slot %d), single %d'
          % (len(pair_of), len(used), len(js['codes'])))

    # ── Q2 引擎格有墨率 (只用 PHI 覆盖的行) ──
    noink = []
    for s, chs in sorted(used.items()):
        r, c = s // NCOL, s % NCOL
        if r not in PHI:
            continue
        x = 16 * ((c + PHI[r]) % 64)
        y = yrow(r)
        if inkat(x, y) == 0:
            noink.append((s, r, c, x, y, ''.join(chs)))
    n_cov = sum(1 for s in used if (s // NCOL) in PHI)
    print('\n[Q2] 已用 pair 落点有墨: %d/%d (PHI 覆盖行)' % (n_cov - len(noink), n_cov))
    if noink:
        print('     无墨的: %s' % noink[:20])

    # 落在 row 24 的已用 pair?
    r24 = sorted(s for s in used if s // NCOL == 24)
    print('     [Q1b] 已用 pair 落在 row 24 的: %d 个 %s' % (len(r24), [(''.join(used[s]), s) for s in r24[:10]]))

    # ── Q3 x 回绕格 ──
    wrap = [(s, c + PHI[s // NCOL]) for s in used if (s // NCOL) in PHI
            and c_of(s) + PHI[s // NCOL] >= 64] if False else []
    wrap_used = []
    for s in sorted(used):
        r, c = s // NCOL, s % NCOL
        if r not in PHI:
            continue
        if c + PHI[r] >= 64:
            wrap_used.append((s, r, c, c + PHI[r]))
    print('\n[Q3] 已用 pair 中 x 需要回绕的: %d 个' % len(wrap_used))
    for s, r, c, cc in wrap_used[:40]:
        x = 16 * (cc % 64)
        print('     slot=%-4d row=%-2d col=%-2d col+PHI=%-3d → x=%-4d  y=%d 墨=%d | y+1 墨=%d | 右侧 x+16 y 墨=%d'
              % (s, r, c, cc, x, yrow(r), inkat(x, yrow(r)), inkat(x, yrow(r) + 1),
                 inkat(x + 16, yrow(r)) if x + 16 < w else -1))

    # ── Q4 空位 ──
    free = [s for s in range(SLOTS) if s not in used]
    print('\n[Q4] 空位 %d 个' % len(free))
    by_row = Counter(s // NCOL for s in free)
    print('     按 row: %s' % sorted(by_row.items()))
    clean, dirty, norow = [], [], []
    for s in free:
        r, c = s // NCOL, s % NCOL
        if r not in PHI:
            norow.append(s)
            continue
        x = 16 * ((c + PHI[r]) % 64)
        y = yrow(r)
        n = inkat(x, y)
        # 同时看 legacy 格 (预检口径) 里有没有墨
        lx = tcslib.atlas_cell_xy(s)[0]
        ln = inkat(lx, tcslib.atlas_cell_xy(s)[1])
        (clean if (n == 0 and ln == 0) else dirty).append((s, r, c, x, y, n, lx, ln))
    print('     引擎格真空(含 legacy 格也空) = %d ; 有墨/legacy格有墨 = %d ; 无 PHI 行(row24) = %d'
          % (len(clean), len(dirty), len(norow)))
    print('     无 PHI 行的 slot: %s' % norow)
    db = Counter(d[1] for d in dirty)
    print('     有墨空位按 row: %s' % sorted(db.items()))

    # ── Q5 legacy 差异 ──
    diff = 0
    for s in range(SLOTS):
        r, c = s // NCOL, s % NCOL
        ph = PHI.get(r)
        ex = 16 * ((c + ph) % 64) if ph is not None else None
        lx = tcslib.atlas_cell_xy(s)[0]
        if ex is None or ex != lx:
            diff += 1
    print('\n[Q5] 引擎格 x != legacy x 的 slot: %d / %d' % (diff, SLOTS))
    print('     legacy x = 4+16*col; 引擎 x = 16*((col+PHI[row])%64)')
    return 0


def c_of(s):
    return s % NCOL


if __name__ == '__main__':
    sys.exit(main())
