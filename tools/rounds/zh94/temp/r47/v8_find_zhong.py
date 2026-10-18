# -*- coding: utf-8 -*-
r"""v8_find_zhong.py — round47 实机帧分析: 在抓帧里找「中」, 并逐像素对比两个盘。

用法:
  python v8_find_zhong.py <dumpA> <tagA> <dumpB> <tagB> [--out <前缀>]

做法:
  1. 用各盘图集里「中」那一格 (912..927, 338..353) 的**墨迹图案**当模板,
     在每帧上做滑窗匹配 (先按"墨点数量"筛, 再逐像素比), 找 0 误差的位置;
  2. 找到后把该位置 ±(24,20) 的窗口在两盘间做逐像素比较, 并打印 ASCII;
  3. 同时给出"整帧逐像素差异"统计 (排除目标窗口) ⇒ 验收要求"其余画面 0 帧差异"。
"""
import io
import os
import sys

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))


def load_frames(d):
    fs = sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))
    return [(f, os.path.join(d, f)) for f in fs]


def frame_gray(p):
    im = Image.open(p)
    a = np.asarray(im.convert('L'))
    return a


def find_pattern(img, tpl, ink_dark=True):
    """在 img 里找 tpl (布尔墨窗) 的 0 误差落点。返回 [(x,y)]。"""
    h, w = tpl.shape
    H, W = img.shape
    dark = (img < 128) if ink_dark else (img > 128)
    n = int(tpl.sum())
    if n == 0:
        return []
    # 先按"目标区域墨点数 == n"筛
    from numpy.lib.stride_tricks import sliding_window_view
    sw = sliding_window_view(dark.astype(np.uint8), (h, w))
    cnt = sw.sum(axis=(2, 3))
    cand = np.argwhere(cnt == n)
    hits = []
    for (y, x) in cand:
        if (sw[y, x] == tpl).all():
            hits.append((int(x), int(y)))
    return hits


def main():
    a = sys.argv[1:]
    dumpA, tagA, dumpB, tagB = a[0], a[1], a[2], a[3]
    prefix = a[a.index('--out') + 1] if '--out' in a else os.path.join(HERE, 'frames')
    sys.path.insert(0, os.path.join(HERE, '..', '..', '..', '..', '..', 'tools', 'text_csv'))
    import tcslib                                                       # noqa: E402
    sys.path.insert(0, os.path.join(HERE, '..', '..', '..', '..', '..', 'tools', 'iso_build'))
    sys.path.insert(0, HERE)
    from r47lib import load                                          # noqa: E402
    # 「中」的图集格 (单字节 0xD6 记录矩形)
    A = load('GR_ZH96_fix')
    eng = A['eng']
    tpl = eng[338:354, 912:928]
    print('「中」模板墨点 %d 个 (图集 912..927 × 338..353)' % tpl.sum())

    fa, fb = load_frames(dumpA), load_frames(dumpB)
    print('A(%s) %d 帧; B(%s) %d 帧' % (tagA, len(fa), tagB, len(fb)))
    common = sorted(set(x[0] for x in fa) & set(x[0] for x in fb))
    print('同名帧 %d 个' % len(common))
    hitsum = 0
    for name in common:
        ia = frame_gray(os.path.join(dumpA, name))
        ib = frame_gray(os.path.join(dumpB, name))
        if ia.shape != ib.shape:
            print('  %s 尺寸不同 %s vs %s' % (name, ia.shape, ib.shape))
            continue
        ha = find_pattern(ia, tpl)
        hb = find_pattern(ib, tpl)
        d = int((ia != ib).sum())
        if ha or hb or d:
            print('  %s: A 命中 %s  B 命中 %s  整帧差异 %d' % (name, ha[:4], hb[:4], d))
        if ha:
            hitsum += 1
            if len(ha) == len(hb) and ha == hb:
                x, y = ha[0]
                wa = ia[max(0, y - 6):y + 22, max(0, x - 8):x + 24]
                wb = ib[max(0, y - 6):y + 22, max(0, x - 8):x + 24]
                nd = int((wa != wb).sum())
                print('      → 窗口(中 ±) 差异 %d 像素' % nd)
                if nd:
                    ys, xs = np.where(wa != wb)
                    print('        差异坐标 (相对窗口): %s' % list(zip(ys.tolist(), xs.tolist()))[:30])
                    for tag, w in (('A', wa), ('B', wb)):
                        print('        --- %s %s ---' % (tag, name))
                        for yy in range(w.shape[0]):
                            print('        |%s|' % ''.join('#' if w[yy, xx] < 128 else '.'
                                                           for xx in range(w.shape[1])))
    print('共 %d 帧命中「中」' % hitsum)


if __name__ == '__main__':
    main()
