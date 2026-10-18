# -*- coding: utf-8 -*-
r"""p14_runnerup.py — 对 9 个「模板非满分」的字, 看**次优位置**离公式预测格有多远。

如果预测格的 mismatch 明显小于全图集其它任何位置 ⇒ 位置判定正确, 差异只来自字形风格。
"""
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
import json                                                         # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
W, H = 1024, 512
CHARS = '档角勿些药博共参惨'


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
    pair_of = json.load(open(tcslib.CHARSET, encoding='utf-8'))['pair_of']
    fnt = ImageFont.truetype(FZ, 16)

    for ch in CHARS:
        b1, b2 = pair_of[ch]
        s = tcslib.pair_slot(b1, b2)
        ex, ey = tcslib.atlas_cell_xy_engine(s)
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        tpl = np.asarray(img)[8:24, 8:24] < 128
        tot = int(tpl.sum())
        allpos = []
        for y in range(0, H - 15):
            win = sliding_window_view(INK[y:y + 16], (16, 16))[0]
            mt = (win != tpl).sum(axis=(1, 2))
            for x in np.nonzero(mt <= mt.min())[0]:
                allpos.append((int(mt[x]), int(x), y))
        allpos.sort()
        here = int((INK[ey:ey + 16, ex:ex + 16] != tpl).sum())
        others = [t for t in allpos if abs(t[1] - ex) > 20]
        bestother = others[0] if others else None
        print('%-2s slot=%-4d 公式预测 (%4d,%3d) mismatch=%-3d (模板墨 %2d) | 全图集最优 %s | '
              '**离预测格 20px 以外的次优** %s'
              % (ch, s, ex, ey, here, tot, allpos[0], bestother))
    return 0


if __name__ == '__main__':
    sys.exit(main())
