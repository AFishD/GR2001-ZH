# -*- coding: utf-8 -*-
r"""cap_montage.py — 由 ab_diff.json 自动生成"同帧放大对照图" (左=修前 / 中=修后 / 右=差异)。

用法:
  python cap_montage.py <dirA> <dirB> <ab_diff.json> --outdir <目录>
                        [--frame snap_00001900.png] [--pad 10] [--zoom 10]
                        [--label-a 修前] [--label-b 修后]

自动行为:
  · 对 ab_diff.json 里每一个"有差异帧", 用它自己的差异包围盒 (带 --pad 边距) 裁同一块区域;
  · 最近邻放大 --zoom 倍, 三格拼接, 顶上写 "帧名 / bbox / 差异像素数";
  · 差异格: 以"修后"为底, 把差异像素涂红 (半透明) ⇒ 一眼看出少了什么;
  · 另外生成 <outdir>/fig_full_<帧名>.png: 整帧并排 (不放大), 给人看上下文。
"""
import io
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    a = sys.argv[1:]
    da, db, dj = a[0], a[1], a[2]
    outdir = a[a.index('--outdir') + 1] if '--outdir' in a else os.path.join(HERE, 'figs')
    pad = int(a[a.index('--pad') + 1]) if '--pad' in a else 10
    zoom = int(a[a.index('--zoom') + 1]) if '--zoom' in a else 10
    la = a[a.index('--label-a') + 1] if '--label-a' in a else 'A (修前)'
    lb = a[a.index('--label-b') + 1] if '--label-b' in a else 'B (修后)'
    only = a[a.index('--frame') + 1] if '--frame' in a else None
    os.makedirs(outdir, exist_ok=True)
    doc = json.load(io.open(dj, encoding='utf-8'))
    recs = [r for r in doc['detail'] if 'n' in r]
    if only:
        recs = [r for r in recs if r['frame'] == only]
    made = []
    for r in recs:
        nm = r['frame']
        ia = Image.open(os.path.join(da, nm)).convert('RGB')
        ib = Image.open(os.path.join(db, nm)).convert('RGB')
        W, H = ia.size
        x0 = max(0, r['x0'] - pad); x1 = min(W, r['x1'] + 1 + pad)
        y0 = max(0, r['y0'] - pad); y1 = min(H, r['y1'] + 1 + pad)
        ca = ia.crop((x0, y0, x1, y1))
        cb = ib.crop((x0, y0, x1, y1))
        aa, bb = np.asarray(ca), np.asarray(cb)
        d = np.any(aa != bb, axis=2)
        cd = bb.copy()
        cd[d] = (255, 40, 40)
        cdi = Image.fromarray(cd)
        w, h = ca.size
        zw, zh = w * zoom, h * zoom
        aa2 = ca.resize((zw, zh), Image.NEAREST)
        bb2 = cb.resize((zw, zh), Image.NEAREST)
        dd2 = cdi.resize((zw, zh), Image.NEAREST)
        bar = 26
        out = Image.new('RGB', (zw * 3 + 8, zh + bar), (16, 16, 16))
        dr = ImageDraw.Draw(out)
        hdr = '%s  bbox x=%d..%d y=%d..%d (%dx%d)  差异像素=%d' % (
            nm, r['x0'], r['x1'], r['y0'], r['y1'], r['w'], r['h'], r['n'])
        dr.text((4, 4), hdr, fill=(255, 255, 0))
        dr.text((4, 14), la, fill=(200, 220, 255))
        dr.text((zw + 12, 14), lb, fill=(200, 255, 200))
        dr.text((zw * 2 + 20, 14), 'DIFF (红=差异像素)', fill=(255, 160, 160))
        out.paste(aa2, (0, bar))
        out.paste(bb2, (zw + 4, bar))
        out.paste(dd2, (zw * 2 + 8, bar))
        p = os.path.join(outdir, 'fig_%s.png' % os.path.splitext(nm)[0])
        out.save(p)
        made.append(p)
        # 整帧并排
        full = Image.new('RGB', (W * 2 + 4, H + bar), (16, 16, 16))
        df = ImageDraw.Draw(full)
        df.text((4, 4), '%s  %s' % (nm, hdr), fill=(255, 255, 0))
        df.text((4, 14), la, fill=(200, 220, 255))
        df.text((W + 8, 14), lb, fill=(200, 255, 200))
        full.paste(ia, (0, bar))
        full.paste(ib, (W + 4, bar))
        p2 = os.path.join(outdir, 'full_%s.png' % os.path.splitext(nm)[0])
        full.save(p2)
        made.append(p2)
        print('  %s  px=%d bbox(%d,%d)-(%d,%d) → %s' % (nm, r['n'], x0, y0, x1, y1, p))
    print('共生成 %d 个文件 → %s' % (len(made), outdir))


if __name__ == '__main__':
    main()
