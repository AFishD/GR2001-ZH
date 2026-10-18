# -*- coding: utf-8 -*-
r"""p07_wrap_truth.py — x 回绕列 (col+PHI>=64) 的字形到底在哪? 全图集穷举模板搜索。

对每个抽样字, 在图集 (1024x512) 上穷举所有 (x,y), 取 mismatch 最小的前 8 个位置。
⇒ 用来判断「x = 16*((col+PHI)%64)」对回绕列是否成立, 以及真实落点在哪。
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import numpy as np                                                  # noqa: E402
from numpy.lib.stride_tricks import sliding_window_view              # noqa: E402
from PIL import Image, ImageDraw, ImageFont                         # noqa: E402
import tcslib                                                       # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
W, H, NCOL = 1024, 512, tcslib.NCOL
PHI = {0: 6, 1: 6, 2: 6, 3: 6, 4: 12, 5: 12, 6: 12, 7: 12, 8: 18, 9: 18, 10: 18, 11: 18,
       12: 24, 13: 30, 14: 30, 15: 30, 16: 30, 17: 36, 18: 36,
       19: 2, 20: 2, 21: 2, 22: 2, 23: 2, 24: 0}
TARGETS = ['死', '骸', '坠', '托', '几', '戒', '僵', '撑', '蔽', '鱼',
           '世', '举', '的', '螺', '区']


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

    def render(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        return win if win.any() else None

    def scan(tpl):
        """全图集穷举: 返回 best 列表 [(mismatch, x, y)] (前 10)。"""
        tot = int(tpl.sum())
        out = []
        for y in range(0, H - 15):
            band = INK[y:y + 16]
            win = sliding_window_view(band, (16, 16))[0]          # (1009,16,16)
            mt = (win != tpl).sum(axis=(1, 2))
            mn = int(mt.min())
            if mn <= max(0, tot // 6):
                for x in np.nonzero(mt == mn)[0]:
                    out.append((mn, int(x), y))
        out.sort()
        return out

    for ch in TARGETS:
        if ch not in pair_of:
            print('%-3s 不在 charset' % ch)
            continue
        b1, b2 = pair_of[ch]
        s = (b1 - tcslib.LEAD_LO) * 94 + (b2 - tcslib.LEAD_LO)
        r, c = s // NCOL, s % NCOL
        ph = PHI[r]
        tpl = render(ch)
        if tpl is None:
            print('%-3s 方正像素16 无字形' % ch)
            continue
        ex = (16 * ((c + ph) % 64), yrow(r))
        nx = (16 * c, yrow(r))
        lx = (4 + 16 * c, yrow(r))
        hit = scan(tpl)
        mt = {}

        def mm(p):
            x, y = p
            if x < 0 or y < 0 or x + 16 > W or y + 16 > H:
                return 999
            return int((INK[y:y + 16, x:x + 16] != tpl).sum())

        mt['engine'] = mm(ex)
        mt['nophase'] = mm(nx)
        mt['legacy'] = mm(lx)
        top = hit[:6]
        print('%-3s slot=%-4d %02X%02X row=%-2d col=%-2d PHI=%-2d wrap=%-3s 模板墨=%-3d | '
              'engine(%4d,%3d)=%-4d nophase(%4d,%3d)=%-4d legacy(%4d,%3d)=%-4d | 全图 best: %s'
              % (ch, s, b1, b2, r, c, ph, 'Y' if c + ph >= 64 else '',
                 int(tpl.sum()), ex[0], ex[1], mt['engine'], nx[0], nx[1], mt['nophase'],
                 lx[0], lx[1], mt['legacy'], top))
    return 0


if __name__ == '__main__':
    sys.exit(main())
