# -*- coding: utf-8 -*-
"""r50 临时: 快速统计「字形是否少了底行」—— 全量扫描 + 与 TTF 模板比对。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))

import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402
from PIL import Image, ImageDraw, ImageFont            # noqa: E402

FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)
_tpl_cache = {}


def tpl(ch):
    if ch in _tpl_cache:
        return _tpl_cache[ch]
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    win = a[8:24, 8:24] < 128
    _tpl_cache[ch] = win
    return win


def scan(iso, charset):
    font = dump_font.load_font(iso)
    gray = dump_font.atlas_gray(font['atlas'], view='engine')
    W, H = font['atlas']['w'], font['atlas']['h']
    A = np.frombuffer(gray, np.uint8).reshape(H, W)
    ink = (A == 0)
    cs = tcslib.Charset(charset) if charset else tcslib.Charset()
    stat = dict(n=0, empty=0, row15=0, bleed16=0, tpl_row15=0, lost_row15=0,
                tpl_bottomlost=0, row0=0, col0=0, col15=0)
    lost = []
    for ch, (b1, b2) in sorted(cs.enc_pair.items(), key=lambda kv: tcslib.pair_slot(*kv[1])):
        if not (tcslib.PAIR_LEAD_LO <= b1 < tcslib.PAIR_LEAD_HI):
            continue
        slot = tcslib.pair_slot(b1, b2)
        x, y = tcslib.atlas_cell_xy_engine_view(slot)
        w = ink[y:y + 16, x:x + 16]
        if w.shape != (16, 16):
            continue
        stat['n'] += 1
        n = int(w.sum())
        if n == 0:
            stat['empty'] += 1
            continue
        r15 = int(w[15].sum())
        bleed = int(ink[y + 16, x:x + 16].sum()) if y + 16 < H else 0
        if r15:
            stat['row15'] += 1
        if bleed:
            stat['bleed16'] += 1
        if int(w[0].sum()):
            stat['row0'] += 1
        if int(w[:, 0].sum()):
            stat['col0'] += 1
        if int(w[:, 15].sum()):
            stat['col15'] += 1
        t = tpl(ch)
        if not t.any():
            continue
        t15 = int(t[15].sum())
        if t15:
            stat['tpl_row15'] += 1
            if r15 == 0:
                stat['lost_row15'] += 1
                lost.append((ch, slot, slot // 62, slot % 62, x, y, n, t15,
                             int((w[:15] != t[:15]).sum()), int((w[:15] & t[:15]).sum())))
    return stat, lost, cs


for tag, iso, charset in (
        ('GR_ZH98 (现役)', 'work/builds/GR_ZH98/GR_ZH98.iso', None),
        ('GR_ZH97', 'work/builds/GR_ZH97/GR_ZH97.iso',
         'work/builds/GR_ZH98/temp/charset_before_font_cleanup.json'),
        ('GR_EN_ORIG', 'work/builds/GR_EN_ORIG/GR_EN_ORIG.iso', None)):
    p = os.path.join(REPO, iso)
    csp = os.path.join(REPO, charset) if charset else None
    st, lost, cs = scan(p, csp)
    print('=== %s  charset pair=%d' % (tag, len(cs.enc_pair)))
    print('   ', json.dumps(st, ensure_ascii=False))
    print('    缺底行(模板第15行有墨但盘上第15行是空) 共 %d 个:' % len(lost))
    for e in lost[:400]:
        print('      %s slot=%4d row=%2d col=%2d (x=%4d,y=%3d) 墨=%3d 模板底行墨=%d 前15行不符=%d 前15行相符=%d'
              % (e[0], e[1], e[2], e[3], e[4], e[5], e[6], e[7], e[8], e[9]))
    rows = {}
    for e in lost:
        rows[e[2]] = rows.get(e[2], 0) + 1
    print('    按行分布:', dict(sorted(rows.items())))
    with io.open(os.path.join(REPO, 'work/builds/GR_ZH98/temp/r50/c1_%s.json'
                              % tag.split()[0]), 'w', encoding='utf-8') as f:
        json.dump(dict(stat=st, lost=[list(e) for e in lost]), f, ensure_ascii=False, indent=1)
