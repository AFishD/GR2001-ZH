# -*- coding: utf-8 -*-
r"""p08_final_grid.py — 用**最终引擎格公式** (含回绕 y+1) 重算全部口径。

最终公式 (本轮实证, 见 docs/REPORT_dump_font_capacity.md):
    slot = (lead-0xA1)*94 + (trail-0xA1)
    row, col = slot//62, slot%62
    p = col + PHI[row]
    x = 16*(p % 64)
    y = yrow(row) + (1 if p >= 64 else 0)        ← 回绕列低 1 行 (p07 实测 8/8 mismatch=0)
    PHI[0..24] (row 24 本轮实测 = 0)
输出: 容量/已用/空位/真空/需回收 + 1319 覆盖复核 + row24 明细。
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
W, H, NCOL = 1024, 512, tcslib.NCOL
LEAD_LO, LEAD_HI = tcslib.LEAD_LO, tcslib.LEAD_HI
SLOTS = (LEAD_HI - LEAD_LO) * 94
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2, 24: 0}
BTN = [0xB1, 0xB5, 0xE7, 0xF1]


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def cell(slot):
    r, c = slot // NCOL, slot % NCOL
    p = c + PHI.get(r, 0)
    return 16 * (p % 64), yrow(r) + (1 if p >= 64 else 0), r, c, p


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
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    iso.close()
    _nm, psm, w, h, clut, px_size, PX = [r for r in tcslib.parse_pak_records(pak)
                                         if r[0] == 'new_font_revised'][0]
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

    _he, faces = tcslib.parse_ft_faces(ft_blob)
    js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
    pair_of = {ch: tuple(v) for ch, v in js['pair_of'].items()}
    singles = {ch: int(v) for ch, v in js['codes'].items()}

    used = {}
    for ch, (b1, b2) in pair_of.items():
        used.setdefault((b1 - LEAD_LO) * 94 + (b2 - LEAD_LO), []).append(ch)

    print('=' * 78)
    print('最终引擎格公式: x=16*((col+PHI[row])%64), y=yrow(row)+(1 if col+PHI>=64 else 0)')
    print('=' * 78)
    print('\n[1] 容量: lead 0x%02X..0x%02X (%d) × trail 0xA1..0xFE (94) = %d'
          % (LEAD_LO, LEAD_HI - 1, LEAD_HI - LEAD_LO, SLOTS))

    bad = [s for s in used if ink(*cell(s)[:2]) == 0]
    print('[2] 已用 pair %d 个 → 引擎格有墨 %d / 无墨 %d' % (len(used), len(used) - len(bad), len(bad)))
    if bad:
        print('    无墨: %s' % [(''.join(used[s]), s, cell(s)) for s in bad[:20]])

    wrap_used = sum(1 for s in used if cell(s)[4] >= 64)
    print('[3] 其中 x 回绕 (col+PHI>=64, y 低 1 行) 的已用 pair: %d' % wrap_used)

    free = [s for s in range(SLOTS) if s not in used]
    clean = [s for s in free if ink(*cell(s)[:2]) == 0]
    dirty = [s for s in free if ink(*cell(s)[:2]) > 0]
    print('[4] 空位 %d = 引擎格真空 %d + 引擎格有墨(需回收) %d' % (len(free), len(clean), len(dirty)))
    print('    真空按 row: %s' % sorted(Counter(s // NCOL for s in clean).items()))
    print('    有墨按 row: %s' % sorted(Counter(s // NCOL for s in dirty).items()))
    print('    真空 slot 列表: %s' % clean)

    # 单字节
    print('\n[5] 单字节码: 已用 %d 个' % len(singles))
    b1 = set(v[0] for v in pair_of.values())
    allb = set(range(0x80, 0x100))
    free_b = sorted(allb - set(singles.values()) - b1)
    print('    0x80..0xFF 里既不是单字节映射、也不是任何 pair lead 的字节 (%d 个): %s'
          % (len(free_b), ['%02X' % b for b in free_b]))
    print('    其中按键图标码 (用户译文里 {{BTN:E0XX}} 用到): %s'
          % ['%02X' % b for b in free_b if b in BTN])
    print('    ⇒ 实际可用单字节码 = %d' % len([b for b in free_b if b not in BTN]))

    print('\n[6] 字符总数: charset = single %d + pair %d = %d ; dump 口径 = + ASCII 95 + icon %d = %d'
          % (len(singles), len(pair_of), len(singles) + len(pair_of),
             len(free_b), len(singles) + len(pair_of) + 95 + len(free_b)))

    tot = w * h
    print('\n[7] 图集 %dx%d = %d texel; 墨 %d (%.2f%%)' % (w, h, tot, ink(0, 0, w, h),
                                                          100.0 * ink(0, 0, w, h) / tot))
    return 0


if __name__ == '__main__':
    sys.exit(main())
