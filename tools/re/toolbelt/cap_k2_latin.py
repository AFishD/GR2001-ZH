# -*- coding: utf-8 -*-
r"""cap_k2_latin.py -- ★ §16.4-1 判据取证: 拉丁文档案名 `TEQSUNSET` 的实拍逐像素对比

    python tools/re/toolbelt/cap_k2_latin.py --base-dump <dump_base> --new-dump <dump_final> \
        --frames 2700 --out work/builds/GR_FA2400_K2/temp

产出:
  latin_f2700_cmp.png     上=基底 GR_ZH124 / 下=成品 (同一帧、同一裁剪、4x 放大)
  latin_f2700_diff.png    逐像素差异图 (黑=相同)
  latin_report.json       {frame: {crop, 不同像素数, 基底墨量, 成品墨量, 判定}}

★ 判据: 档案名区域与基底**逐像素相同** ⇒ "清晰可读、不糊" (没有任何一像素来自被覆盖的
  ASCII 表或搬错位的字形)。
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                    # noqa: E402
from PIL import Image                                                 # noqa: E402

# 档案名框 (基底帧 583x437 坐标系; 由 temp/_probe_crop.png 目视 + 亮点行分布定出)
BOX = (104, 104, 216, 156)
ZOOM = 4


def load(dump, frame):
    p = os.path.join(dump, 'snap_f%08d.png' % frame)
    if not os.path.isfile(p):
        return None, p
    return np.array(Image.open(p).convert('RGB')), p


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-dump', default=os.path.join(REPO, 'work', 'builds', 'GR_CAP2400',
                                                        'temp', 'dump_base'))
    ap.add_argument('--new-dump', default=os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2',
                                                       'temp', 'dump_final'))
    ap.add_argument('--frames', default='2700,1500,2280')
    ap.add_argument('--out', default=os.path.join(REPO, 'work', 'builds', 'GR_FA2400_K2',
                                                  'temp'))
    a = ap.parse_args(argv)
    os.makedirs(a.out, exist_ok=True)
    res = {}
    for fr in [int(x) for x in a.frames.split(',') if x.strip()]:
        ib, pb = load(a.base_dump, fr)
        inw, pn = load(a.new_dump, fr)
        if ib is None or inw is None:
            print('[skip] frame %d 缺帧: %s / %s' % (fr, pb, pn))
            res[fr] = dict(missing=True, base=os.path.isfile(pb), new=os.path.isfile(pn))
            continue
        if ib.shape != inw.shape:
            print('[warn] frame %d 尺寸不同: %s vs %s' % (fr, ib.shape, inw.shape))
        x0, y0, x1, y1 = BOX
        cb, cn = ib[y0:y1, x0:x1], inw[y0:y1, x0:x1]
        d = (cb != cn).any(axis=2)
        n = int(d.sum())
        # 墨量: 亮像素 (档案名是白字)
        ink_b = int((cb.astype(int).sum(axis=2) > 560).sum())
        ink_n = int((cn.astype(int).sum(axis=2) > 560).sum())
        # 拼图: 上=基底 / 下=成品 / 最下=差异
        gap = np.full((4, cb.shape[1], 3), 255, dtype=np.uint8)
        diff_img = np.zeros_like(cb)
        diff_img[d] = [255, 0, 0]
        stack = np.concatenate([cb, gap, cn, gap, diff_img], axis=0)
        im = Image.fromarray(stack).resize((stack.shape[1] * ZOOM, stack.shape[0] * ZOOM),
                                           Image.NEAREST)
        p1 = os.path.join(a.out, 'latin_f%d_cmp.png' % fr)
        im.save(p1, optimize=True)
        Image.fromarray((d * 255).astype(np.uint8)).resize(
            (d.shape[1] * ZOOM, d.shape[0] * ZOOM), Image.NEAREST).save(
            os.path.join(a.out, 'latin_f%d_diff.png' % fr), optimize=True)
        res[fr] = dict(crop=list(BOX), diff_px=n, base_ink=ink_b, new_ink=ink_n,
                       identical=(n == 0), png=os.path.relpath(p1, REPO).replace('\\', '/'),
                       base_png=os.path.relpath(pb, REPO).replace('\\', '/'),
                       new_png=os.path.relpath(pn, REPO).replace('\\', '/'))
        print('[f%-5d] 裁剪 %s: 不同像素 **%d** / %d ; 墨 基底 %d vs 成品 %d ⇒ %s'
              % (fr, BOX, n, d.size, ink_b, ink_n,
                 '**逐像素相同 ✓**' if n == 0 else '✗ 有差异'))
    with io.open(os.path.join(a.out, 'latin_report.json'), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    print('[out] %s' % os.path.join(a.out, 'latin_report.json'))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
