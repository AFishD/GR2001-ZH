# -*- coding: utf-8 -*-
r"""p22_grid.py — 出「字库格位占用图」: 重排前 vs 重排后 (一眼看清空位从哪来)。"""
import io
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
from PIL import Image, ImageDraw, ImageFont                  # noqa: E402
import numpy as np                                              # noqa: E402
import tcslib                                                   # noqa: E402
import dump_font                                                # noqa: E402
import repack_font                                              # noqa: E402

# 中文字体 (PIL 默认位图字体没有汉字 ⇒ 会画成方块)
FONT_CAND = [r'C:\Windows\Fonts\msyh.ttc', r'C:\Windows\Fonts\simhei.ttf',
             r'C:\Windows\Fonts\Deng.ttf']
FONT_PATH = next((p for p in FONT_CAND if os.path.isfile(p)), None)
F12 = ImageFont.truetype(FONT_PATH, 13) if FONT_PATH else ImageFont.load_default()
F14 = ImageFont.truetype(FONT_PATH, 15) if FONT_PATH else ImageFont.load_default()

NCOL, CW, CH = tcslib.NCOL, tcslib.CW, tcslib.CH
CELL = 18
PAD = 46
LEGEND = 150
TITLE = 30
# 配色
C_USED = (214, 92, 92)          # 已用字形
C_FREE = (255, 255, 255)        # 空且能用 (可直接写新字)
C_DIRTY = (170, 214, 255)       # 空但格里有旧墨 (重排后可回收)
C_BLOCK = (150, 150, 150)       # 被记录码/图标占死 (永远不能用)
C_EDGE = (120, 120, 120)


def build(iso, cs, charset_path):
    font = dump_font.load_font(iso)
    am = font['atlas']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    protect, _r = repack_font.protect_mask(font['faces'], am['w'], am['h'])
    cells = repack_font.enumerate_cells(am['w'], am['h'])
    cls = repack_font.classify(cells, protect, am['w'], am['h'])
    items, _dead = repack_font.char_order(cs)
    used = set(s for s, _c in items)
    return A, cells, cls, used


def classify_cell(A, c, k, used):
    s = c['slot']
    if s in used:
        return C_USED
    if k != 'usable':
        return C_BLOCK
    ink = A.eng[c['y']:c['y'] + CH, c['x']:c['x'] + CW].any()
    return C_DIRTY if ink else C_FREE


def draw(img, d, y0, title, A, cells, cls, used):
    d.text((6, y0 + 6), title, fill=(0, 0, 0), font=F14)
    top = y0 + TITLE
    n_used = n_free = n_dirty = n_block = 0
    for c in cells:
        s, r, col = c['slot'], c['row'], c['col']
        colr = classify_cell(A, c, cls[s][0], used)
        if colr == C_USED:
            n_used += 1
        elif colr == C_FREE:
            n_free += 1
        elif colr == C_DIRTY:
            n_dirty += 1
        else:
            n_block += 1
        x = PAD + col * CELL
        y = top + r * CELL
        d.rectangle([x, y, x + CELL - 1, y + CELL - 1], fill=colr, outline=C_EDGE)
    # 行号 / 列号
    for r in range(25):
        d.text((4, top + r * CELL + 3), '%2d' % r, fill=(70, 70, 70), font=F12)
    for col in range(0, NCOL, 10):
        d.text((PAD + col * CELL + 2, top - 15), '%d' % col, fill=(70, 70, 70), font=F12)
    # 图例
    lx = PAD + NCOL * CELL + 14
    items = [('已用字形 %d' % n_used, C_USED),
             ('**空·能用** %d' % n_free, C_FREE),
             ('空但有旧墨 %d' % n_dirty, C_DIRTY),
             ('占死(记录码/图标) %d' % n_block, C_BLOCK)]
    for i, (txt, colr) in enumerate(items):
        yy = top + 8 + i * 26
        d.rectangle([lx, yy, lx + 16, yy + 16], fill=colr, outline=C_EDGE)
        d.text((lx + 22, yy + 1), txt, fill=(0, 0, 0), font=F12)
    d.text((lx, top + 8 + 4 * 26 + 14), '每格 = 一个 16x16 字形位', fill=(90, 90, 90), font=F12)
    d.text((lx, top + 8 + 4 * 26 + 30), '行 24 只有 0..15 列有效', fill=(90, 90, 90), font=F12)


def main():
    cs94 = tcslib.Charset(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46',
                                       'charset_before_repack.json'))
    cs95 = tcslib.Charset()
    A94, cells, cls94, used94 = build(os.path.join(REPO, 'work', 'builds', 'GR_ZH94',
                                                   'GR_ZH94.iso'), cs94, None)
    A95, _c, cls95, used95 = build(os.path.join(REPO, 'work', 'builds', 'GR_ZH95',
                                                'GR_ZH95.iso'), cs95, None)
    w = PAD + NCOL * CELL + 14 + LEGEND + 10
    h = 2 * (TITLE + 25 * CELL + 16) + 10
    img = Image.new('RGB', (w, h), (250, 250, 250))
    d = ImageDraw.Draw(img)
    draw(img, d, 0, 'BEFORE  GR_ZH94 (交付盘): 空位被冲散, 50 个可用格还糊着旧墨',
         A94, cells, cls94, used94)
    draw(img, d, TITLE + 25 * CELL + 26,
         'AFTER   GR_ZH95 (重排后): 字形压到最前, 其余可用格全部清零',
         A95, cells, cls95, used95)
    op = os.path.join(REPO, 'docs', 'img')
    os.makedirs(op, exist_ok=True)
    p = os.path.join(op, 'r46_grid_occupancy.png')
    img.save(p, optimize=True)
    print('-> %s %s' % (p, img.size))


if __name__ == '__main__':
    main()
