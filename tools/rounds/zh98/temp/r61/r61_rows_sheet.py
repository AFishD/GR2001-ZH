# -*- coding: utf-8 -*-
r"""r61_rows_sheet.py — 把 recon 每行的截图裁出列表框, 拼成一张对照图 (一行一张, 带标签)。

目的: 用**眼睛**确认第 k 个采样点到底停在哪一行 —— 内存差分的"行号 → 地址"映射必须
      建立在实际行序上, 不能靠 round60 的旧 y 表推。

用法: python work/builds/GR_ZH98/temp/r61/r61_rows_sheet.py <dumpdir> [out.png]
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw                                            # noqa: E402

# 列表框裁切窗口 (左栏; 含 10 行标签)
BOX = (40, 68, 300, 362)


def main():
    d = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(d, 'r61_rows_sheet.png')
    names = ['row%02d.png' % k for k in range(9)] + ['row_interview.png']
    tiles = []
    for n in names:
        p = os.path.join(d, n)
        if os.path.isfile(p):
            tiles.append((n, Image.open(p).convert('RGB').crop(BOX)))
    if not tiles:
        sys.exit('没有可用的行截图')
    w, h = tiles[0][1].size
    LW, COLS = 96, 2
    rows = (len(tiles) + COLS - 1) // COLS
    sheet = Image.new('RGB', (COLS * (LW + w), h * rows), (20, 20, 20))
    dr = ImageDraw.Draw(sheet)
    for i, (n, im) in enumerate(tiles):
        cx, cy = (i % COLS) * (LW + w), (i // COLS) * h
        sheet.paste(im, (cx + LW, cy))
        dr.text((cx + 6, cy + h // 2), n.replace('.png', ''), fill=(255, 255, 0))
    sheet.save(out)
    print('写出 %s  (%dx%d, %d 行, %d 列)' % (out, sheet.width, sheet.height, rows, COLS))
    return 0


if __name__ == '__main__':
    sys.exit(main())
