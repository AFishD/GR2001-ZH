# -*- coding: utf-8 -*-
r"""crop_dirty.py — 裁 中(912,338) 附近的图集, 对比 GR_ZH93/94; 并在文本表里找 抖"""
import csv
import io
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

CASES = [
    ('GR_ZH93(修前)', os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font',
                                 'GR_ZH93_font_atlas_1x.png')),
    ('GR_ZH94(修后)', os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'release', 'font',
                                 'GR_ZH94_font_atlas_1x.png')),
]
BOX = (880, 320, 1000, 400)          # 中 的矩形 (912..928, 338..354) 附近
for tag, p in CASES:
    if not os.path.isfile(p):
        print('%s: 缺 %s' % (tag, p))
        continue
    im = Image.open(p).convert('L')
    print('%s  %s' % (tag, im.size))
    crop = im.crop(BOX)
    z = 6
    crop = crop.resize((crop.width * z, crop.height * z), Image.NEAREST)
    out = os.path.join(HERE, 'crop_%s.png' % ('93' if '93' in tag else '94'))
    crop.save(out)
    print('  → %s (%dx%d)' % (os.path.relpath(out, REPO), crop.width, crop.height))
    # 打印 中 矩形下边界那几行 (v=354..360) 在 u=900..940 的墨点
    px = im.load()
    print('  v=352..362, u=900..940 的墨点位置:')
    for v in range(352, 363):
        xs = [u for u in range(900, 941) if px[u, v] < 128]
        print('    v=%3d  n=%2d  %s' % (v, len(xs), xs[:24]))

# 文本表里找 抖 / 中
print()
print('=== 文本表里的 中 / 抖 ===')
for n in sorted(os.listdir(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'text'))):
    if not n.endswith('.csv'):
        continue
    for r in csv.DictReader(io.open(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'text', n),
                                    encoding='utf-8-sig')):
        t = r['text_edited']
        if '中' in t or '抖' in t:
            i = t.find('抖') if '抖' in t else t.find('中')
            print('  %s/%s: …%s…' % (n.replace('GR_ZH94_text_', '').replace('.csv', ''),
                                     r['id'], t[max(0, i - 12):i + 12]))
