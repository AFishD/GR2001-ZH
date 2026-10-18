# -*- coding: utf-8 -*-
r"""p04_phi_row24.py — 用 FT 记录里落在网格行上的单字节字形, **实测**每一行的相位 PHI。

方法: 单字节码的记录 (u0,v0) 就是引擎的 UV 起点; 引擎采样 = ((u0 + 16*PHI[row]) % 1024, v0+1)。
⇒ 对每个已知行, 枚举 ph ∈ 0..63, 看哪个 ph 让**该行全部记录**的采样窗都有墨。
   · 行 11 / 18 / 19 是已知行 (PHI = 18 / 36 / 2) ⇒ 用来验证方法本身;
   · 行 24 (v0=434) 没有 PKI 表项 ⇒ 本轮实测补上。
"""
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
W, H = 1024, 512
PHI_KNOWN = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
             12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
             19: 2, 20: 2, 21: 2, 22: 2, 23: 2}


def yrow(r):
    return tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0))


def row_of_v(v0):
    for r in range(40):
        if yrow(r) == v0:
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
    dfault = faces[fi['default']][2]
    large = faces[fi['large']][2]
    import json
    js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
    singles = {int(v): ch for ch, v in js['codes'].items()}

    byrow = defaultdict(list)
    for fi_name, recs in (('default', dfault), ('large', large)):
        for idx, (b0, b1, u0, v0, u1, v1) in enumerate(recs):
            if u1 <= u0 or v1 <= v0:
                continue
            if v0 == 452 or v0 == 482 or v0 == 395 or v0 == 420:
                continue                                     # EN 带 / 非网格带
            r = row_of_v(v0)
            if r is None:
                continue
            byrow[r].append((fi_name, idx, idx + 0x20, u0, v0, u1, v1,
                             singles.get(idx + 0x20, '')))

    print('== 落在网格行上的 FT 记录 (按行) ==')
    for r in sorted(byrow):
        known = PHI_KNOWN.get(r, None)
        print('  row %-2d (y=%3d): %2d 条  已知 PHI=%s  u0 列表=%s'
              % (r, yrow(r), len(byrow[r]), known, sorted(set(t[3] for t in byrow[r]))))

    print('\n== 逐行实测相位: 枚举 ph, 要求该行**全部**记录的采样窗 (u0+16*ph, v0+1) 有墨 ==')
    for r in sorted(byrow):
        rows = byrow[r]
        good = []
        for ph in range(64):
            ok = 0
            for (_fn, _idx, _code, u0, v0, _u1, _v1, _ch) in rows:
                if ink((u0 + 16 * ph) % W, v0 + 1) > 0:
                    ok += 1
            if ok == len(rows):
                good.append(ph)
        known = PHI_KNOWN.get(r, None)
        verdict = ''
        if known is not None:
            verdict = ('  ← 已知 PHI=%d: %s' % (known, '✓ 命中' if known in good else '✗ 未命中!'))
        print('  row %-2d  记录 %2d 条  通过全部记录的 ph = %-28s%s'
              % (r, len(rows), good, verdict))

    # 行 24 的逐条细节
    print('\n== row 24 (v0=434) 逐条细节 ==')
    for (fn, idx, code, u0, v0, u1, v1, ch) in byrow.get(24, []):
        inks = ['%d:%d' % (ph, ink((u0 + 16 * ph) % W, v0 + 1)) for ph in range(0, 64)]
        nz = [t for t in inks if not t.endswith(':0')]
        print('  %-8s code=0x%02X %-3s rec=(%d,%d,%d,%d) 有墨的 ph: %s'
              % (fn, code, ch, u0, v0, u1, v1, ' '.join(nz)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
