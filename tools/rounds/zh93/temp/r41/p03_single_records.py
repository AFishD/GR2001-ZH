# -*- coding: utf-8 -*-
r"""p03_single_records.py — 单字节码 / ASCII 的 FT 记录 → 引擎采样点 实证。

对每条记录 (ASCII 0x20..0x7E + 单字节码):
  raw  = 墨(记录矩形 u0,v0,u1,v1)                    ← tcslib._check_record 的第 1 判据
  du   = 墨(矩形 +4/+2)                              ← 第 2 判据
  tol  = 墨(矩形 ±4/±2)                              ← 第 3 判据
  eng  = 墨((u0 + 16*PHI[row(v0)]) % 1024, v0+1 起 16x16) ← 报告 PLAN_C §3.2 的引擎采样
判据: 引擎采样点有墨 ⇒ 这个字真画得出来。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
W, H = 1024, 512
Y0, CH, SKIP_ROW, SKIP_ROWS = 2, 16, 12, 3
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def row_of_v(v0):
    """v0 → 引擎行 r (yrow(r) == v0)。返回 None 表示 v0 不在网格行上。"""
    if (v0 - Y0) % CH:
        return None
    q = (v0 - Y0) // CH
    if q <= SKIP_ROW - 1 + 0 and q < SKIP_ROW:
        return q
    for r in range(64):
        y = Y0 + CH * (r + (SKIP_ROWS if r >= SKIP_ROW else 0))
        if y == v0:
            return r
    return None


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

    _he, faces = tcslib.parse_ft_faces(ft_blob)
    fi = {f[0]: i for i, f in enumerate(faces)}
    print('faces: %s' % [(f[0], len(f[2])) for f in faces])
    dfault = faces[fi['default']][2]
    print('default face 记录数 = %d' % len(dfault))

    # v0 → 行 的分布
    from collections import Counter
    rows_v0 = Counter(r[3] for r in dfault if r[4] > r[2] and r[5] > r[3])
    print('default face 有效记录的 v0 分布 (前 20): %s' % sorted(rows_v0.items())[:20])
    norow = [v0 for v0 in rows_v0 if row_of_v(v0) is None]
    print('v0 不在任何网格行上的: %s' % norow)

    js = __import__('json').load(open(tcslib.CHARSET, encoding='utf-8'))
    singles = {int(v): ch for ch, v in js['codes'].items()}
    # 只看真实会画的: ASCII 0x20..0x7E + 单字节码
    codes = sorted(set(range(0x20, 0x7F)) | set(singles))

    stat = Counter()
    bad = []
    print('\n%-6s %-5s %-22s %-8s %-6s %-6s %-6s %-22s %-6s'
          % ('code', 'char', 'rec(u0,v0,u1,v1)', 'row(v0)', 'raw', 'du', 'tol', 'engine(x,y)', 'eng'))
    for code in codes:
        idx = code - 0x20
        if idx < 0 or idx >= len(dfault):
            continue
        b0, b1, u0, v0, u1, v1 = dfault[idx]
        if u1 <= u0 or v1 <= v0:
            stat['退化矩形'] += 1
            continue
        r = row_of_v(v0)
        raw = ink(u0, v0, u1 - u0, v1 - v0)
        du = ink(u0 + 4, v0 + 2, u1 - u0, v1 - v0)
        tol = ink(u0 - 4, v0 - 2, (u1 - u0) + 8, (v1 - v0) + 4)
        if r is None:
            ex = ey = -1
            eng = -1
        else:
            ex = (u0 + 16 * PHI.get(r, 0)) % W
            ey = v0 + 1
            eng = ink(ex, ey)
        okc = (raw > 0) or (du > 0) or (tol > 0)
        stat['有墨(记录口径)' if okc else '记录口径空白'] += 1
        stat['引擎点有墨' if eng > 0 else ('引擎点空' if eng == 0 else '无行')] += 1
        if eng <= 0 or not okc:
            bad.append((code, singles.get(code, ''), (u0, v0, u1, v1), r, raw, du, tol, ex, ey, eng))
        if code <= 0x3F or code in singles:
            print('0x%02X  %-5s (%4d,%3d,%4d,%3d) %-8s %-6d %-6d %-6d (%4d,%3d) %-6d%s'
                  % (code, singles.get(code, ''), u0, v0, u1, v1, r, raw, du, tol, ex, ey, eng,
                     '' if okc else '  <<记录口径空白'))
    print('\n统计: %s' % dict(stat))
    print('\n== 有问题的 (引擎采样点无墨 或 记录口径空白) ==')
    for t in bad:
        print('  0x%02X %-3s rec=%s row=%s raw=%d du=%d tol=%d engine=(%d,%d) eng=%d' % t)
    return 0


if __name__ == '__main__':
    sys.exit(main())
