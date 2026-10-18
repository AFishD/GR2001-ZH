# -*- coding: utf-8 -*-
r"""p19_missing22.py — GR_ZH92 上那 22 个「引擎格只有 1 行渗漏墨」的字, 字形到底在不在盘上?

对每个字: 全图集穷举方正像素16 模板, 报全局最佳位置 + 与引擎格/legacy 格的关系。
结论决定了「拿 GR_ZH92 当 src 注入现役 charset 会不会画出 22 个空白字」。
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
import csv                                                          # noqa: E402
import io                                                           # noqa: E402

FZ = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
W, H = 1024, 512
SAMPLE = '米斤倍延栓偏'


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


def main():
    cs = tcslib.Charset()
    # 用户译文里到底用到了这 22 个里的哪几个?
    txtdir = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'text')
    used = set()
    for fn in sorted(os.listdir(txtdir)):
        if not fn.endswith('.csv'):
            continue
        with io.open(os.path.join(txtdir, fn), encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                t = row.get('text_edited') or ''
                used.update(t)
    print('用户原表 %s: 用到的字符 %d 个' % (os.path.relpath(txtdir, REPO), len(used)))

    fnt = ImageFont.truetype(FZ, 16)

    def render(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        return win if win.any() else None

    for name in ('GR_ZH92', 'GR_ZH93'):
        ink = atlas_of(name)
        print('\n===== %s =====' % name)
        for ch in SAMPLE:
            b1, b2 = cs.enc_pair[ch]
            s = tcslib.pair_slot(b1, b2)
            ex, ey = tcslib.atlas_cell_xy_engine(s)
            lx, ly = tcslib.atlas_cell_xy(s)
            tpl = render(ch)
            tot = int(tpl.sum())
            best = (10 ** 9, -1, -1)
            for y in range(0, H - 15):
                win = sliding_window_view(ink[y:y + 16], (16, 16))[0]
                mt = (win != tpl).sum(axis=(1, 2))
                mn = int(mt.min())
                if mn < best[0]:
                    best = (mn, int(np.argmin(mt)), y)
            e_all = int(ink[ey:ey + 16, ex:ex + 16].sum())
            e_body = int(ink[ey + 1:ey + 16, ex:ex + 16].sum())
            l_all = int(ink[ly:ly + 16, lx:lx + 16].sum())
            print('  %s %02X%02X slot=%-4d pair=%s引擎格(%4d,%3d)[墨%3d/体%3d] legacy(%4d,%3d)[墨%3d] '
                  '| 全图集最优 mismatch=%-3d @(%4d,%3d) %s'
                  % (ch, b1, b2, s, '★在译文里 ' if ch in used else '          ',
                     ex, ey, e_all, e_body, lx, ly, l_all, best[0], best[1], best[2],
                     ('= 引擎格 ✓' if (best[1], best[2]) == (ex, ey) else
                      ('= legacy 格' if (best[1], best[2]) == (lx, ly) else '= 别处'))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
