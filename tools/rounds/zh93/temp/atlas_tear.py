# -*- coding: utf-8 -*-
r"""atlas_tear.py — 看"每隔 4 行撕裂"到底是什么: 大区域裁图 + 行/列统计"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CASES = [
    ('现役盘', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font',
                          'GR_ZH93_font_atlas_1x.png')),
    ('英文原盘', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'temp', 'r43', 'orig',
                            'GR_EN_ORIG_text.csv', 'GR_EN_ORIG_font_atlas.png')),
]
for tag, p in CASES:
    if not os.path.isfile(p):
        print('%s: 缺 %s' % (tag, p))
        continue
    im = Image.open(p).convert('L')
    w, h = im.size
    print('%s: PNG %dx%d' % (tag, w, h))
    # 归一化到 1024 宽
    sc = max(1, w // 1024)
    px = im.load()
    W, H = w // sc, h // sc
    print('  归一化 1x: %dx%d' % (W, H))
    # 每 4 行分组, 看组内行墨点数的"突变"
    prof = [sum(1 for x in range(0, W) if px[x * sc, y * sc] < 128) for y in range(min(H, 64))]
    print('  前 32 行墨点: %s' % prof[:32])
    # 找"行内墨点分布在 4 的倍数上有异常"的行
    print('  每行: 墨点数 / 最左墨点x / 最右墨点x')
    for y in range(min(20, H)):
        xs = [x for x in range(0, W) if px[x * sc, y * sc] < 128]
        if xs:
            print('    y=%2d  n=%4d  x∈[%d,%d]' % (y, len(xs), xs[0], xs[-1]))
        else:
            print('    y=%2d  n=   0  (空)' % y)
    # 裁图
    box = (0, 0, min(256, W) * sc, min(80, H) * sc)
    crop = im.crop(box)
    crop = crop.resize((crop.width * 2, crop.height * 2), Image.NEAREST)
    out = os.path.join(HERE, 'tear_%s.png' % ('zh' if '现役' in tag else 'en'))
    crop.save(out)
    print('  裁图 → %s' % os.path.relpath(out, REPO))
    print()
