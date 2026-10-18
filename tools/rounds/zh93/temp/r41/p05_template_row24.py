# -*- coding: utf-8 -*-
r"""p05_template_row24.py — 用「方正像素16 模板比对」**定死** row 24 的相位。

方法 (与 docs/REPORT_plan_c_zh93.md 的 m20_judge.py 同法):
  把 16x16 字形从 TTF 渲染成二值模板 (gen_font16 同口径: 32x32 画布 @(8,8), 取 [8:24) 窗),
  在图集里**穷举**所有 (x, y) 位置, 数「模板 vs 图集」不一致像素; 0 = 逐像素完全一致。
  · 先用已知行的单字节码做**方法自检**: 期望命中 (u0 + 16*PHI[row], v0+1) 附近;
  · 再对 row 24 (v0=434) 的 7 个码定出真实落点 ⇒ 反解 PHI[24]。
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
W, H = 1024, 512
PHI_KNOWN = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
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
    ft_blob = b''.join(s[0] for s in tcslib.lzo_subs(iso.read(ft_e['iso_off'], ft_e['stored'])))
    iso.close()
    rec = [r for r in tcslib.parse_pak_records(pak) if r[0] == 'new_font_revised'][0]
    _nm, psm, w, h, clut, px_size, PX = rec
    nb = np.frombuffer(pak[PX:PX + W * H // 2], dtype=np.uint8).reshape(H, W // 2)
    A = np.empty((H, W), dtype=np.uint8)
    A[:, 0::2] = nb & 0x0F
    A[:, 1::2] = (nb >> 4) & 0x0F
    INK = (A == 0)

    _he, faces = tcslib.parse_ft_faces(ft_blob)
    fi = {f[0]: i for i, f in enumerate(faces)}
    dfault = faces[fi['default']][2]
    js = json.load(open(tcslib.CHARSET, encoding='utf-8'))
    singles = {int(v): ch for ch, v in js['codes'].items()}

    fnt = ImageFont.truetype(FZ, 16)

    def render(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        if not win.any():
            return None
        return win

    def best_positions(tpl, y_lo, y_hi):
        """在 y ∈ [y_lo, y_hi) 内穷举 x, 返回按 (mismatch, x, y) 排序的前若干."""
        out = []
        for y in range(y_lo, min(y_hi, H - 16 + 1)):
            for x in range(0, W - 16 + 1):
                win = INK[y:y + 16, x:x + 16]
                out.append((int((win != tpl).sum()), x, y))
        out.sort()
        return out

    def probe(label, code, expect_x=None):
        idx = code - 0x20
        if not (0 <= idx < len(dfault)):
            print('  %s code=0x%02X 无记录' % (label, code))
            return
        b0, b1, u0, v0, u1, v1 = dfault[idx]
        ch = singles.get(code)
        if not ch:
            print('  %s code=0x%02X 无字符名' % (label, code))
            return
        tpl = render(ch)
        if tpl is None:
            print('  %s %r 方正像素16 无字形' % (label, ch))
            return
        top = best_positions(tpl, max(0, v0 - 6), v0 + 8)
        m0 = top[0]
        z = [t for t in top if t[0] == 0]
        print('  %s code=0x%02X %-2s rec.u0=%-4d v0=%-3d 模板墨=%2d | best=(%4d,%3d) mismatch=%d'
              ' | 0 误差位置 %s'
              % (label, code, ch, u0, v0, int(tpl.sum()), m0[1], m0[2], m0[0],
                 ('%d 个: %s' % (len(z), [(t[1], t[2]) for t in z[:6]])) if z else '无'))
        if expect_x is not None:
            print('       期望 (若 PHI 成立) x = (%d + 16*PHI) %% 1024' % u0)

    print('== 方法自检: 已知行 (row 11 / 18 / 19) 的单字节码 ==')
    for code in sorted(singles):
        idx = code - 0x20
        if not (0 <= idx < len(dfault)):
            continue
        _b0, _b1, u0, v0, _u1, _v1 = dfault[idx]
        r = {yrow(rr): rr for rr in range(40)}.get(v0)
        if r in (11, 18, 19) and code in (0x92, 0x9D, 0xAF, 0xC9, 0xB7):
            probe('自检 row %-2d' % r, code)
    # 上面按码位过滤可能空; 再补几个该行的
    for target_row, codes in ((11, [0x92, 0x9D, 0xAF]), (18, [0xC9, 0xCA]), (19, [0xB7])):
        for code in codes:
            idx = code - 0x20
            if 0 <= idx < len(dfault):
                _b0, _b1, u0, v0, _u1, _v1 = dfault[idx]
                if v0 == yrow(target_row):
                    probe('自检 row %-2d' % target_row, code)

    print('\n== 目标: row 24 (v0=434) 的 7 个码 ==')
    for idx, (b0, b1, u0, v0, u1, v1) in enumerate(dfault):
        if v0 != 434 or u1 <= u0:
            continue
        probe('row24', idx + 0x20)

    print('\n== 对照: row 24 上「有墨的 16px 格」 ==')
    y = yrow(24)
    cells = [(x, int(INK[y:y + 16, x:x + 16].sum())) for x in range(0, W, 16)]
    print('  y=%d: 有墨的列 = %s' % (y, [(x // 16, n) for x, n in cells if n]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
