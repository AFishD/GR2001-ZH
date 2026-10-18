# -*- coding: utf-8 -*-
r"""fa_cross_hunt.py — 在图集/记录表里找「叉形(X/×)」字形候选（只读）

    python tools/re/toolbelt/fa_cross_hunt.py --iso work/builds/GR_F364/GR_F364.iso --ncol 62 --tag f364

做法: 用 方正像素16.ttf 渲染的 '×'/'X' 模板与**每一个** 16x16 候选窗逐 texel 比对 (XOR 距离),
      候选窗 = ① 544 条 FT 记录矩形  ② 槽 0..1871 的引擎格。
      输出距离最小的前若干名 + 拼图 PNG, 供人眼确认盘上到底有没有现成的叉形字形。
"""
import argparse
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np                                                     # noqa: E402
import fa_recon as R                                                   # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_FA2400', 'temp')
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')


def render16(ch):
    from PIL import Image, ImageDraw, ImageFont
    fnt = ImageFont.truetype(FZ16, 16)
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    return a[8:24, 8:24] < 128


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', required=True)
    ap.add_argument('--tag', required=True)
    ap.add_argument('--ncol', type=int, default=62)
    ap.add_argument('--topn', type=int, default=14)
    a = ap.parse_args(argv)
    F = R.read_font(a.iso)
    plane, w, h = F['plane'], F['w'], F['h']
    R.P('=' * 92)
    R.P('fa_cross_hunt.py  %s  %dx%d  ncol=%d' % (a.iso, w, h, a.ncol))
    R.P('=' * 92)
    tpls = {}
    for ch in ('×', 'X', 'x'):
        t = render16(ch)
        tpls[ch] = t
        R.P('模板 %r: 墨 %d' % (ch, int(t.sum())))

    cands = []          # (kind, label, g)
    for (nm, fld, rows) in F['faces']:
        for i, (_o, r) in enumerate(rows):
            u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
            if u1 - u0 != 16 or v1 - v0 != 16 or v0 < 0 or u0 < 0 or v1 > h or u1 > w:
                continue
            g = R.window(plane, w, u0, v0, 16, 16)
            if g.sum() == 0:
                continue
            cands.append(('rec', '%s idx%d code0x%02X' % (nm, i, i + 0x20), g))
    nrow = 0
    while 2 + 16 * (nrow + (3 if nrow >= 12 else 0)) + 16 <= h:
        nrow += 1
    for s in range(0, min(nrow * a.ncol, 1872)):
        cx, cy = R.cell(s, a.ncol)
        g = R.window(plane, w, cx, cy, 16, 16)
        if g.sum() == 0:
            continue
        cands.append(('cell', 'slot%d @(%d,%d)' % (s, cx, cy), g))
    R.P('候选窗 %d 个 (记录 + 槽)' % len(cands))

    res = {}
    for ch, t in tpls.items():
        scored = sorted(((int((g ^ t).sum()), k, lab, g) for (k, lab, g) in cands),
                        key=lambda x: x[0])
        res[ch] = []
        R.P('')
        R.P('── 与模板 %r (墨 %d) 最接近的前 %d 名:' % (ch, int(t.sum()), a.topn))
        for (d, k, lab, g) in scored[:a.topn]:
            R.P('   XOR 距离 %3d  墨 %3d  [%s] %s' % (d, int(g.sum()), k, lab))
            res[ch].append(dict(dist=d, kind=k, label=lab, ink=int(g.sum())))
        # 拼图
        from PIL import Image
        S, pad = 6, 4
        n = a.topn
        sheet = Image.new('L', (n * (16 * S + pad) + pad, 16 * S + 2 * pad), 255)
        for i, (d, k, lab, g) in enumerate(scored[:n]):
            tile = Image.fromarray(np.where(g, 0, 255).astype(np.uint8), 'L').resize(
                (16 * S, 16 * S), Image.NEAREST)
            sheet.paste(tile, (pad + i * (16 * S + pad), pad))
        p = os.path.join(OUT, 'crosshunt_%s_%04X.png' % (a.tag, ord(ch)))
        sheet.save(p)
        R.P('   → 拼图 %s (从左到右 = 上面第 1..%d 名)' % (p, n))
    with io.open(os.path.join(OUT, 'crosshunt_%s.json' % a.tag), 'w', encoding='utf-8',
                 newline='\n') as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
