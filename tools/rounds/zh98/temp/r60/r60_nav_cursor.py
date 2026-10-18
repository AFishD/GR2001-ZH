# -*- coding: utf-8 -*-
r"""r60_nav_cursor.py — 从抓到的帧里**量化**特别收录列表的光标位置 (高亮条 y)。

做法: 在左侧列表框 (x 60..275, y 70..358 —— **排除底部状态条** y365..367 的金色)
      里找金色像素最多的那一行 y, 取金色**连通带**的中心 → 映射到列表行号。
输出: 每一帧的光标行 (只在变化时打印) + 每个按键窗口内的位移。
"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image                                                    # noqa: E402

D = sys.argv[1] if len(sys.argv) > 1 else \
    r'work/builds/GR_TEST_FONT1/temp/dump_r60sfint'
F0 = int(sys.argv[2]) if len(sys.argv) > 2 else 23800
F1 = int(sys.argv[3]) if len(sys.argv) > 3 else 30300
ROWS = [(85, '1 影片'), (114, '2 设定图'), (144, '3 音乐'), (173, '4 武器'),
        (203, '5 奖章'), (233, '6 背景'), (262, '7 专家(空条)'), (292, '8 屏幕截图'),
        (321, '9 访谈'), (351, '10 预告片')]


def gold_band(im):
    """返回 (band_center_y, band_len)。只在左侧列表框内找 (排除底部状态条)。"""
    px = im.convert('RGB').load()
    ys = []
    for y in range(70, 359):
        n = 0
        for x in range(60, 275):
            r, g, b = px[x, y]
            if r > 100 and 70 < g < 150 and b < 80 and r - b > 60:
                n += 1
        if n > 120:                       # 一行里 >120 个金色像素 = 高亮条的一部分
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
        return None
    for (ry, nm) in ROWS:
        if abs(cy - ry) <= 13:
            return nm
    return 'y=%.0f(非列表行)' % cy


frames = sorted(f for f in os.listdir(D) if f.startswith('snap_f') and f.endswith('.png'))
sel = [f for f in frames if F0 <= int(f[6:14]) <= F1]
print('帧 %d 张 (%s .. %s)' % (len(sel), sel[0], sel[-1]))
prev, traj = None, []
for f in sel:
    fr = int(f[6:14])
    cy, blen = gold_band(Image.open(os.path.join(D, f)))
    row = row_of(cy)
    traj.append((fr, row, cy))
    if row != prev:
        print('  F%-6d → %-18s (金带中心 y=%.0f, 长 %d)' % (fr, row or '(无)', cy or -1, blen))
        prev = row

print('\n按键窗口 (每 500 帧一次 down) 前后的光标:')
KEYS = list(range(24300, 27801, 500)) + [28800]
for k in KEYS:
    before = next((t[1] for t in reversed(traj) if k - 400 <= t[0] < k and t[1]), None)
    after = next((t[1] for t in traj if k < t[0] <= k + 450 and t[1]), None)
    print('  F%-6d 按前 %-18s 按后 %-18s' % (k, before, after))
