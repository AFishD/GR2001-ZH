# -*- coding: utf-8 -*-
r"""p13_nonmatch.py — 无偏抽样: 对偶字的字形在**整张图集**上的全局最佳匹配落在哪?

方法: 每 33 个对偶字抽 1 个 (共 ~40 个, 确定性抽样), 用方正像素16 模板在全图集
(1024x512) 穷举, 取 mismatch 最小的位置, 然后看它与「引擎格公式预测的位置」差多少。
输出: 公式命中率 + 没命中时差在哪 —— 用来量化 PHI 拟合的**残余不确定性**。
"""
import json
import os
import sys
from collections import Counter

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
W, H = 1024, 512
STEP = 33


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
    pairs = sorted(json.load(open(tcslib.CHARSET, encoding='utf-8'))['pair_of'].items(),
                   key=lambda kv: tcslib.pair_slot(*kv[1]))
    fnt = ImageFont.truetype(FZ, 16)

    def render(ch):
        img = Image.new('L', (32, 32), 255)
        ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
        a = np.asarray(img)
        win = a[8:24, 8:24] < 128
        return win if win.any() else None

    # 预先把每个 y 的窗口 mismatch 图算好 (按模板). 逐模板扫全图集。
    stat = Counter()
    detail = []
    for (ch, (b1, b2)) in pairs[::STEP]:
        tpl = render(ch)
        if tpl is None:
            stat['方正像素16 无字形'] += 1
            continue
        tot = int(tpl.sum())
        best = (10 ** 9, -1, -1)
        for y in range(0, H - 15):
            win = sliding_window_view(INK[y:y + 16], (16, 16))[0]
            mt = (win != tpl).sum(axis=(1, 2))
            mn = int(mt.min())
            if mn < best[0]:
                best = (mn, int(np.argmin(mt)), y)
        s = tcslib.pair_slot(b1, b2)
        ex, ey = tcslib.atlas_cell_xy_engine(s)
        row, col = s // tcslib.NCOL, s % tcslib.NCOL
        ph = tcslib.atlas_row_phase(row)
        wrap = col + ph >= tcslib.GRID_MOD
        # 引擎格的两个候选: (x, yrow) 与回绕时的 (x, yrow+1)
        cands = [(ex, ey), (ex, ey - 1), (ex, ey + 1)]
        bx, by = best[1], best[2]
        verdict = '其他地方'
        if best[0] <= 2:
            if (bx, by) == (ex, ey):
                verdict = '引擎格(公式预测位置)'
            elif by == ey and abs(bx - ex) <= 1:
                verdict = '引擎格 ±1 px'
            elif (bx, by) == (ex, ey - 1) and wrap:
                verdict = '引擎格 y-1 (回绕列公式预测 y+1?)'
            else:
                verdict = '其他位置'
        elif best[0] <= 8:
            verdict = '近似命中(非 FZXS16 字形)'
        else:
            verdict = '全图集都找不到 (非本字体/被覆盖)'
        stat[verdict] += 1
        detail.append((ch, s, row, col, ph, wrap, ex, ey, bx, by, best[0], tot, verdict))

    print('抽样 %d 个对偶字 (每 %d 个取 1 个), 全图集穷举模板搜索:' % (len(detail), STEP))
    print('%-3s %-5s %-4s %-4s %-4s %-5s %-12s %-12s %-7s %-7s %s'
          % ('字', 'slot', 'row', 'col', 'PHI', '回绕', '公式预测', '全局最佳', 'mism', '模板墨', '判定'))
    for d in detail:
        print('%-3s %-5d %-4d %-4d %-4d %-5s (%4d,%3d)  (%4d,%3d)  %-7d %-7d %s'
              % (d[0], d[1], d[2], d[3], d[4], 'Y' if d[5] else '', d[6], d[7], d[8], d[9],
                 d[10], d[11], d[12]))
    print('\n== 汇总 ==')
    for k, v in stat.most_common():
        print('  %-34s %d' % (k, v))
    return 0


if __name__ == '__main__':
    sys.exit(main())
