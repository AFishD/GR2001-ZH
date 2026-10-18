# -*- coding: utf-8 -*-
r"""p17_yan_template.py — 延 的字形在 GR_ZH92 / GR_ZH93 图集上到底长什么样?

GR_ZH91/92 的引擎格 (512,354) 只有 10 个墨点 (ZH93 有 67) ⇒ 必须确认那 10 点是
「延 的字形」而不是别的字的碎片。方法: 方正像素16 模板 + 全图集穷举 + 打印 16x16 位图。
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

FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
W, H = 1024, 512


def atlas_of(name):
    p = os.path.join(REPO, 'work', 'builds', name, name + '.iso')
    iso = tcslib.Iso(p)
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
    return (A == 0)


def show(ink, x, y, title):
    print('  %s @(%d,%d) 墨=%d' % (title, x, y, int(ink[y:y + 16, x:x + 16].sum())))
    for r in range(16):
        print('    ' + ''.join('#' if ink[y + r, x + c] else '.' for c in range(16)))


def main():
    cs = tcslib.Charset()
    ch = '延'
    s = tcslib.pair_slot(*cs.enc_pair[ch])
    ex, ey = tcslib.atlas_cell_xy_engine(s)
    lx, ly = tcslib.atlas_cell_xy(s)
    fnt = ImageFont.truetype(FZ, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    tpl = np.asarray(img)[8:24, 8:24] < 128
    print('%s slot=%d  引擎格=(%d,%d)  legacy=(%d,%d)  模板墨=%d'
          % (ch, s, ex, ey, lx, ly, int(tpl.sum())))
    print('\n== 方正像素16 模板 ==')
    for r in range(16):
        print('    ' + ''.join('#' if tpl[r, c] else '.' for c in range(16)))

    for name in ('GR_ZH92', 'GR_ZH93'):
        ink = atlas_of(name)
        print('\n===== %s =====' % name)
        show(ink, ex, ey, '引擎格')
        if (lx, ly) != (ex, ey):
            show(ink, lx, ly, 'legacy 格')
        # 全图集穷举
        best = (10 ** 9, -1, -1)
        for y in range(0, H - 15):
            win = sliding_window_view(ink[y:y + 16], (16, 16))[0]
            mt = (win != tpl).sum(axis=(1, 2))
            mn = int(mt.min())
            if mn < best[0]:
                best = (mn, int(np.argmin(mt)), y)
        here = int((ink[ey:ey + 16, ex:ex + 16] != tpl).sum())
        print('  → 引擎格 mismatch=%d ; 全图集最优 (mismatch=%d) @(%d,%d)'
              % (here, best[0], best[1], best[2]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
