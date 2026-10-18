# -*- coding: utf-8 -*-
r"""ab1_framescan.py — round47 实机 A/B 第 1 步: 在两轮抓帧里找「中」字帧。

用法:
  python ab1_framescan.py <dumpA> <tagA> [<dumpB> <tagB>]

做法:
  · 用两盘各自的图集里「中」(单字节码 0xD6) 那一格当模板:
      修前 GR_ZH94 那格带溢出墨 (下方多一条横条), 修后 GR_ZH96_fix 那格干净;
    在屏幕上做 0 误差滑窗命中 ⇒ 该帧真的画出了这个字。
  · 对每一帧记录命中位置; 两轮同名帧再比整帧差异像素数。
输出 JSON + 文本日志。
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
R47 = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, R47)


def frames(d):
    return sorted(f for f in os.listdir(d) if f.startswith('snap_') and f.endswith('.png'))


def gray(p):
    return np.asarray(Image.open(p).convert('L'))


def find_all(img, tpl):
    """在 img 里找 tpl(布尔墨窗, True=墨) 的 0 误差落点 → [(x, y)]"""
    dark = (img < 128).astype(np.uint8)
    h, w = tpl.shape
    if dark.shape[0] < h or dark.shape[1] < w:
        return []
    sw = sliding_window_view(dark, (h, w))
    n = int(tpl.sum())
    cand = np.argwhere(sw.sum(axis=(2, 3)) == n)
    return [(int(x), int(y)) for y, x in cand if (sw[y, x] == tpl).all()]


def main():
    a = sys.argv[1:]
    dumps = []
    i = 0
    while i + 1 < len(a):
        dumps.append((a[i], a[i + 1]))
        i += 2

    import r47lib                                                   # noqa: E402
    tp = {}
    for ver in ('GR_ZH94', 'GR_ZH96_fix'):
        A = r47lib.load(ver)
        r = r47lib.default_rects(A['faces'])[0xD6]      # 「中」= 单字节 0xD6
        u0, v0, u1, v1 = r
        g = A['eng'][v0:v1 + 1, u0:u1 + 1]
        tp[ver] = ((u0, v0, u1, v1), (g < 128))
        print('%s 「中」记录矩形 u=%d..%d v=%d..%d  墨点(v<128)=%d'
              % (ver, u0, u1, v0, v1, int((g < 128).sum())))
    print()

    out = {}
    for (d, tag) in dumps:
        fs = frames(d)
        print('=== %s : %s  共 %d 帧 ===' % (tag, d, len(fs)))
        rows = []
        for f in fs:
            p = os.path.join(d, f)
            img = gray(p)
            rec = dict(frame=f)
            hitA = find_all(img, tp['GR_ZH94'][1])
            hitB = find_all(img, tp['GR_ZH96_fix'][1])
            if hitA:
                rec['hit94'] = hitA[:8]
            if hitB:
                rec['hit96'] = hitB[:8]
            if hitA or hitB:
                print('  %s  hit94=%s  hit96=%s'
                      % (f, rec.get('hit94'), rec.get('hit96')))
                rows.append(rec)
        out[tag] = dict(dir=d, nframes=len(fs), hits=rows)
        print('  → 命中帧 %d' % len(rows))
        print()

    io.open(os.path.join(HERE, 'ab1_framescan.json'), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print('→ %s' % os.path.join(HERE, 'ab1_framescan.json'))


if __name__ == '__main__':
    main()
