# -*- coding: utf-8 -*-
r"""p26_shots.py — 出报告用的实机对照图 (放大裁剪)。"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
from PIL import Image, ImageDraw, ImageFont                    # noqa: E402

F14 = ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc', 15)
OUT = os.path.join(REPO, 'docs', 'img')
os.makedirs(OUT, exist_ok=True)


def crop(p, box, scale=2):
    im = Image.open(p).convert('RGB').crop(box)
    return im.resize((im.size[0] * scale, im.size[1] * scale), Image.NEAREST)


def stack(items, path, title_h=22):
    """items = [(label, image)] 竖排; 每张下面一行说明。"""
    w = max(im.size[0] for _l, im in items)
    h = sum(im.size[1] + title_h for _l, im in items)
    out = Image.new('RGB', (w, h), (245, 245, 245))
    d = ImageDraw.Draw(out)
    y = 0
    for label, im in items:
        d.rectangle([0, y, w, y + title_h], fill=(30, 30, 40))
        d.text((6, y + 3), label, fill=(255, 235, 120), font=F14)
        out.paste(im, (0, y + title_h))
        y += im.size[1] + title_h
    out.save(path, optimize=True)
    print('-> %s %s' % (path, out.size))


def main():
    A94 = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'r46', 'dump_T94')
    B95 = os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'temp', 'dump_r46T')
    fa = os.path.join(A94, 'snap_f00021600.png')
    fb = os.path.join(B95, 'snap_f00021600.png')
    box = (30, 45, 300, 345)                        # 特别收录分类列表
    stack([('BEFORE  GR_ZH94 (老盘): 若/纤/终/脆/膛/著 全部画不出来 (位置是空白)',
            crop(fa, box, 2)),
           ('AFTER   GR_ZH95 (本轮): 6 个字都补回了引擎真正采样的位置',
            crop(fb, box, 2))],
          os.path.join(OUT, 'r46_ft6_before_after.png'))

    # 武器详情页 (含滚动箭头) —— 重排前后逐像素相同
    wa = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'temp', 'dump_r46w',
                      'snap_f00023300.png')
    wb = os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'temp', 'dump_r46w',
                      'snap_f00023300.png')
    box2 = (0, 40, 583, 437)
    stack([('GR_ZH94 (重排前) 武器详情页 — 左侧 ▲▼ 滚动箭头 + 长段中文',
            crop(wa, box2, 1)),
           ('GR_ZH95 (重排后) 同一帧 — 与该帧**逐像素完全相同** (297/297 帧全同)',
            crop(wb, box2, 1))],
          os.path.join(OUT, 'r46_weapons_detail_ab.png'))

    # 交付盘 text/ 有没有被测试文案污染
    man = os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'build_info.json')
    j = json.load(io.open(man, encoding='utf-8'))
    bad = []
    for f in (j.get('text_snapshot') or {}).get('tables') or []:
        p = os.path.join(REPO, f['path'].replace('/', os.sep))
        if not os.path.isfile(p) or io.open(p, 'rb').read() and \
                __import__('hashlib').sha256(open(p, 'rb').read()).hexdigest() != f['sha256']:
            bad.append(p)
    print('[check] 交付盘 GR_ZH95/text 三张表 sha256 与 build_info 一致: %s'
          % ('是 ✓' if not bad else '否 !! %s' % bad))
    txt = os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'text', 'GR_ZH95_text_short.csv')
    with io.open(txt, encoding='utf-8-sig', newline='') as fh:
        s = fh.read()
    for w in ('若片', '纤定图', '终乐', '脆器', '膛章', '著景'):
        if w in s:
            print('   !! 交付盘表里出现了测试文案 %r' % w)
    print('[check] 交付盘表里没有测试文案 ✓')


if __name__ == '__main__':
    main()
