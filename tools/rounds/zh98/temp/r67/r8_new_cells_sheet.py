# -*- coding: utf-8 -*-
r"""r8_new_cells_sheet.py — 从**交付盘**上把 329 个新字格抠出来拼成一张联系表 (人眼可核)。

每个格 = 盘上引擎图 (16*col, yrow) 的 16x16; 框色 = 与 16px 模板的逐像素比对结果
(绿 = diff_px==0, 红 = 不一致)。盘上取格与模板渲染是两条互不依赖的路径。
用法: python r8_new_cells_sheet.py <iso> <out.png>
"""
import csv
import io
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                            # noqa: E402
import dump_font as D                                                    # noqa: E402

SC = 4
COLS = 24
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
SEL = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_expand_zh113.csv')


def main():
    iso_p, out_p = sys.argv[1], sys.argv[2]
    from PIL import Image, ImageDraw, ImageFont
    rows = list(csv.DictReader(io.open(SEL, encoding='utf-8-sig', newline='')))
    assert len(rows) == 329
    f = D.load_font(iso_p)
    at = f['atlas']
    W, H = at['w'], at['h']
    gray = np.frombuffer(D.atlas_gray(at, 'engine'), dtype=np.uint8).reshape(H, W)
    ink = gray == 0
    fnt = ImageFont.truetype(TTF, 16)

    def tpl(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        return np.asarray(img)[8:24, 8:24] < 128

    nrow = (len(rows) + COLS - 1) // COLS
    cw, chh = 16 * SC + 6, 16 * SC + 20
    im = Image.new('RGB', (COLS * cw + 6, nrow * chh + 6), (250, 250, 250))
    d = ImageDraw.Draw(im)
    f_s = ImageFont.load_default()
    nmatch = 0
    for i, r in enumerate(rows):
        slot = int(r['slot'])
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        blk = ink[y:y + 16, x:x + 16]
        t = tpl(r['char'])
        same = bool((blk == t).all())
        nmatch += same
        sub = np.where(blk, 0, 255).astype(np.uint8)
        a = np.kron(sub, np.ones((SC, SC), dtype=np.uint8))
        ox, oy = 3 + (i % COLS) * cw, 3 + (i // COLS) * chh
        im.paste(Image.fromarray(a, 'L').convert('RGB'), (ox, oy))
        d.rectangle([ox - 1, oy - 1, ox + 16 * SC, oy + 16 * SC],
                    outline=(0, 160, 0) if same else (220, 0, 0))
        d.text((ox, oy + 16 * SC + 3), '%s %s' % (r['new_lead'][2:] + r['new_trail'][2:],
                                                  r['char']), fill=(60, 60, 60), font=f_s)
    im.save(out_p)
    print('[sheet] %s  %dx%d  %d 格; 与模板 diff_px==0 的 = %d / %d'
          % (out_p, im.width, im.height, len(rows), nmatch, len(rows)))
    assert nmatch == len(rows), '有格与模板不一致!'


if __name__ == '__main__':
    main()
