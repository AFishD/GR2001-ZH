# -*- coding: utf-8 -*-
r"""s8_fig.py — 出两张报告插图 (只读, 写 temp/r44/):
  ① fig_artifact_compare.png : 左上角 (0,0)-(512,80) 旧口径(flat) vs 新口径(engine)
  ② fig_rows19_24.png        : 引擎口径图 + 引擎格线, 网格行 19..24 —— 看字形是否落在格里
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                # noqa: E402
from PIL import Image, ImageDraw, ImageFont                       # noqa: E402
import tcslib                                                     # noqa: E402
import dump_font                                                  # noqa: E402
import s3_recon as S3                                             # noqa: E402

F = ImageFont.load_default()


def panel(arr, box, zoom, title, grid=None, marks=None):
    """arr: bool 图 (True=墨) → 裁 box → 放大 zoom → 加标题/网格/标记。"""
    im = Image.fromarray(np.where(arr, 0, 255).astype(np.uint8), 'L').convert('RGB')
    x0, y0, x1, y1 = box
    im = im.crop(box).resize(((x1 - x0) * zoom, (y1 - y0) * zoom), Image.NEAREST)
    d = ImageDraw.Draw(im)
    if grid:
        for (gx, gy, gw, gh, col) in grid:
            d.rectangle([(gx - x0) * zoom, (gy - y0) * zoom,
                         (gx - x0 + gw) * zoom - 1, (gy - y0 + gh) * zoom - 1], outline=col)
    for (mx, my, mw, mh, col) in (marks or []):
        d.rectangle([(mx - x0) * zoom, (my - y0) * zoom,
                     (mx - x0 + mw) * zoom - 1, (my - y0 + mh) * zoom - 1], outline=col)
    # 标题条: 先用 PIL 默认字模画, 再放大 2 倍 (字太小看不清)
    head = Image.new('RGB', (max(1, im.size[0] // 2), 14), (255, 255, 255))
    ImageDraw.Draw(head).text((2, 3), title, fill=(0, 0, 0), font=F)
    head = head.resize((head.size[0] * 2, head.size[1] * 2), Image.NEAREST)
    out = Image.new('RGB', (max(im.size[0], head.size[0]), im.size[1] + head.size[1] + 2),
                    (255, 255, 255))
    out.paste(head, (0, 0))
    out.paste(im, (0, head.size[1] + 2))
    return out


def main():
    iso = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
    font = dump_font.load_font(iso)
    at = font['atlas']
    w, h = at['w'], at['h']
    cs = tcslib.Charset()
    flat = S3.ink_gray(dump_font.atlas_gray(at, view='flat'), w, h)
    eng = S3.ink_gray(dump_font.atlas_gray(at, view='engine'), w, h)

    # ① 左上角对照 (旧口径第一行 = 包头; 新口径第一行空白)
    a = panel(flat, (0, 0, 512, 80), 2,
              'A) OLD (--flat-view): the dashed pixels on row 0 = the 48-byte GIF packet header '
              'painted as pixels; same thing every 64 rows',
              marks=[(0, 0, 96, 1, (255, 0, 0)), (96, 64, 96, 1, (255, 0, 0))])
    b = panel(eng, (0, 0, 512, 80), 2,
              'B) NEW (default = engine view): same area -- rows 0/1 are clean blank, '
              'no packet bytes, no 6-cell shift, no tearing',
              marks=[(0, 0, 96, 1, (0, 160, 0)), (96, 64, 96, 1, (0, 160, 0))])
    out = Image.new('RGB', (max(a.size[0], b.size[0]), a.size[1] + b.size[1] + 8), (255, 255, 255))
    out.paste(a, (0, 0))
    out.paste(b, (0, a.size[1] + 8))
    p1 = os.path.join(HERE, 'fig_artifact_compare.png')
    out.save(p1)

    # ② 网格行 19..24: 引擎格线 vs 字形实际位置 (字形整体偏右 24 格)
    rows = [(r, tcslib.GRID_Y0 + tcslib.CH * (r + (tcslib.GRID_SKIP_ROWS if r >= tcslib.GRID_SKIP_ROW else 0)))
            for r in range(19, 25)]
    y0, y1 = rows[0][1], rows[-1][1] + tcslib.CH
    grid = [(tcslib.CW * c, y, tcslib.CW, tcslib.CH, (255, 120, 120)) for (r, y) in rows
            for c in range(63)]
    marks = []
    for ch in ('螺', '虽', '衍', '衣'):
        p = cs.enc_pair.get(ch)
        if not p:
            continue
        slot = tcslib.pair_slot(*p)
        x, y = tcslib.atlas_cell_xy_engine(slot)
        marks.append((x - tcslib.atlas_flat_x_shift(y) % w if False else x, y, tcslib.CW, tcslib.CH,
                      (40, 130, 255)))
    c = panel(eng, (0, y0, 1024, y1), 2,
              'C) 引擎口径 + 引擎格线(红): 网格行 19..24 —— 字形不在红格里 (整体偏右 24~42 格, 见报告 §4); '
              '蓝框 = 写入侧(flat)格位', grid=grid, marks=marks)
    p2 = os.path.join(HERE, 'fig_rows19_24.png')
    c.save(p2)
    print('[fig] %s (%dx%d)' % (os.path.basename(p1), out.size[0], out.size[1]))
    print('[fig] %s (%dx%d)' % (os.path.basename(p2), c.size[0], c.size[1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
