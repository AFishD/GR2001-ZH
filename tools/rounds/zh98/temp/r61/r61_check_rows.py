# -*- coding: utf-8 -*-
r"""r61_check_rows.py — 从 recon 抓到的 PNG 上量"金色高亮条"的 y, 复核每一行采样的真实行号。

复用 round60 的 gold_band 口径 (左侧列表框 x60..275, y70..358, 排除底部状态条的金色)。
这是**独立于内存钩子**的旁证: 内存钩子说"选中行 = k", 像素说"高亮条在第 k 行"。

用法: python work/builds/GR_ZH98/temp/r61/r61_check_rows.py <dumpdir>
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image                                                    # noqa: E402

ROWS = [(85, '1 影片'), (114, '2 设定图'), (144, '3 音乐'), (173, '4 武器'),
        (203, '5 奖章'), (233, '6 背景'), (262, '7 专家(空条)'), (292, '8 屏幕截图'),
        (321, '9 访谈'), (351, '10 预告片')]


def gold_band(im):
    px = im.convert('RGB').load()
    ys = []
    for y in range(70, 359):
        n = 0
        for x in range(60, 275):
            r, g, b = px[x, y]
            if r > 100 and 70 < g < 150 and b < 80 and r - b > 60:
                n += 1
        if n > 120:
            ys.append(y)
    if not ys:
        return None, 0
    best, cur = [], [ys[0]]
    for y in ys[1:]:
        if y == cur[-1] + 1:
            cur.append(y)
        else:
            best = cur if len(cur) > len(best) else best
            cur = [y]
    best = cur if len(cur) > len(best) else best
    return (best[0] + best[-1]) / 2.0, len(best)


def row_of(cy):
    if cy is None:
        return '(无金带)'
    for (ry, nm) in ROWS:
        if abs(cy - ry) <= 13:
            return nm
    return 'y=%.0f(非列表行)' % cy


def main():
    d = sys.argv[1]
    prefix = sys.argv[2] if len(sys.argv) > 2 else 'row'
    names = ['%s%02d.png' % (prefix, k) for k in range(9)] + \
            ['%s_interview.png' % prefix, 'page_interview.png']
    print('%-26s %-10s %-8s %s' % ('截图', '金带中心y', '带长', '判定行'))
    for n in names:
        p = os.path.join(d, n)
        if not os.path.isfile(p):
            print('%-26s %s' % (n, '(缺)'))
            continue
        cy, blen = gold_band(Image.open(p))
        print('%-26s %-10s %-8d %s' % (n, ('%.0f' % cy) if cy is not None else '-', blen, row_of(cy)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
