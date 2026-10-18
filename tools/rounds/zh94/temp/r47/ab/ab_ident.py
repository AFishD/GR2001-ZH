# -*- coding: utf-8 -*-
r"""ab_ident.py — round47 实机 A/B 第 2 步: 在实机帧里"认字" + 裁图放大对照。

用法:
  python ab_ident.py --before <dirA> --after <dirB> --frames f00024500,f00025600 ...
                     [--sx 1.0,1.05,...] [--sy 0.95,1.0,...] [--outprefix <p>] [--zoom 8]

对每个帧:
  1. 逐像素 diff 找差异簇 (A=修前, B=修后);
  2. 用两盘图集的 16x16 记录格 (修前=带残墨, 修后=干净) 在**多种显示缩放**下做滑窗匹配,
     报出最佳 (码位, 缩放, 位置, 失配数) —— 失配 0 表示"屏幕上画的就是那一格";
  3. 打印该格附近的 ASCII 对照 (A / B), 并裁图放大 (最近邻) 存 PNG 做同帧对照图。
"""
import os
import sys

import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
R47 = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, R47)


def load(d):
    return np.asarray(Image.open(d).convert('RGB'))


def gray(a):
    return (0.299 * a[:, :, 0] + 0.587 * a[:, :, 1] + 0.114 * a[:, :, 2]).astype(np.uint8)


def clusters(mask, gap=3):
    """把差异像素按 y 聚成簇 (简单按行间隔分组), 返回 [(y0,y1,x0,x1,n)]"""
    ys, xs = np.where(mask)
    if len(ys) == 0:
        return []
    order = np.argsort(ys)
    ys, xs = ys[order], xs[order]
    out = []
    cy0 = py = int(ys[0]); cx0 = cx1 = int(xs[0])
    n = 1
    for k in range(1, len(ys)):
        y, x = int(ys[k]), int(xs[k])
        if y - py <= gap:
            cy0 = min(cy0, y); cx0 = min(cx0, x); cx1 = max(cx1, x); n += 1
        else:
            out.append((cy0, py, cx0, cx1, n))
            cy0 = py = y; cx0 = cx1 = x; n = 1
        py = y
    out.append((cy0, py, cx0, cx1, n))
    return out


def resize_bool(t, h, w):
    im = Image.fromarray((t.astype(np.uint8) * 255))
    im = im.resize((w, h), Image.NEAREST)
    return np.asarray(im) > 127


def match_cell(img_g, tpl_bool, cx, cy, rad=3, polarity=True):
    """在 (cx,cy) 附近 ±rad 内滑窗匹配 tpl, 返回 (best_mismatch, best_x, best_y)"""
    h, w = tpl_bool.shape
    ink = (img_g >= 128) if polarity else (img_g < 128)
    H, W = img_g.shape
    best = (1 << 30, -1, -1)
    x0 = max(0, cx - rad); x1 = min(W - w, cx + rad)
    y0 = max(0, cy - rad); y1 = min(H - h, cy + rad)
    if x1 < x0 or y1 < y0:
        return best
    reg = ink[y0:y1 + h, x0:x1 + w]
    if reg.shape[0] < h or reg.shape[1] < w:
        return best
    sw = sliding_window_view(reg.astype(np.uint8), (h, w))
    mism = (sw != tpl_bool[None, None, :, :]).sum(axis=(2, 3))
    k = int(np.argmin(mism))
    yy, xx = divmod(k, mism.shape[1])
    v = int(mism[yy, xx])
    if v < best[0]:
        best = (v, x0 + xx, y0 + yy)
    return best


def ascii_win(g, x0, x1, y0, y1):
    return ['%4d |%s|' % (y, ''.join('#' if g[y, x] < 128 else '.' for x in range(x0, x1)))
            for y in range(y0, y1)]


def main():
    a = sys.argv[1:]
    before = a[a.index('--before') + 1]
    after = a[a.index('--after') + 1]
    fr = a[a.index('--frames') + 1].split(',')
    sx_list = [float(v) for v in (a[a.index('--sx') + 1].split(',')
                                  if '--sx' in a else ['1.0'])]
    sy_list = [float(v) for v in (a[a.index('--sy') + 1].split(',')
                                  if '--sy' in a else ['1.0'])]
    zoom = int(a[a.index('--zoom') + 1]) if '--zoom' in a else 8
    pref = a[a.index('--outprefix') + 1] if '--outprefix' in a else os.path.join(HERE, 'ident')

    import r47lib                                                   # noqa: E402
    import tcslib                                                   # noqa: E402
    A94 = r47lib.load('GR_ZH94')
    A96 = r47lib.load('GR_ZH96_fix')
    cs = tcslib.Charset()
    # 两盘图集不同处 ⇒ 受影响码位
    d = (A94['eng'] != A96['eng'])
    ys, xs = np.where(d)
    print('两盘图集差异 %d 像素; y 取值 %s' % (int(d.sum()), sorted(set(ys.tolist()))))
    r94 = r47lib.default_rects(A94['faces'])
    r96 = r47lib.default_rects(A96['faces'])
    codes = []
    for code in sorted(r94):
        u0, v0, u1, v1 = r94[code]
        if d[v0:v1 + 1, u0:u1 + 1].any():
            codes.append(code)
    print('受影响码位 %d 个: %s' % (len(codes), ' '.join('0x%02X(%s)' % (c, cs.codes.get(c, '?'))
                                                        for c in codes)))
    print()

    for f in fr:
        pa, pb = os.path.join(before, f), os.path.join(after, f)
        if not (os.path.isfile(pa) and os.path.isfile(pb)):
            print('!! 缺帧 %s (%s / %s)' % (f, os.path.isfile(pa), os.path.isfile(pb)))
            continue
        A, B = load(pa), load(pb)
        dm = np.any(A != B, axis=2)
        print('=' * 78)
        print('帧 %s  差异像素 %d' % (f, int(dm.sum())))
        cl = clusters(dm)
        for (y0, y1, x0, x1, n) in cl:
            print('  差异簇 x=%d..%d y=%d..%d  n=%d' % (x0, x1, y0, y1, n))
        ga, gb = gray(A), gray(B)
        # 用第一个簇定位, 认字
        if cl:
            y0, y1, x0, x1, n = cl[0]
            for tag, g, atl in (('A(修前)', ga, A94), ('B(修后)', gb, A96)):
                best = (1 << 30, None, None, None, None)
                for code in codes:
                    u0, v0, u1, v1 = (r94 if atl is A94 else r96)[code]
                    cell = (atl['eng'][v0:v1 + 1, u0:u1 + 1] < 128)
                    for sx in sx_list:
                        for sy in sy_list:
                            h = max(1, int(round(cell.shape[0] * sy)))
                            w = max(1, int(round(cell.shape[1] * sx)))
                            t = resize_bool(cell, h, w)
                            cx = x1 - w + 4          # 条状差异在格内偏左下/右下
                            cy = y1 - h + 1
                            for pol in (True, False):
                                v, mx, my = match_cell(g, t, cx, cy, rad=6, polarity=pol)
                                if v < best[0]:
                                    best = (v, code, (sx, sy), (mx, my, w, h), pol)
                v, code, sc, pos, pol = best
                if code is None:
                    print('  %s: 未能匹配' % tag)
                    continue
                ch = cs.codes.get(code, '?')
                print('  %s: 最佳匹配 0x%02X「%s」 失配=%d  scale=%s  位置=%s  %s'
                      % (tag, code, ch, v, sc, pos, 'light-on-dark' if pol else 'dark-on-light'))
                mx, my, w, h = pos
                x0c, y0c = mx - 3, my - 2
                x1c, y1c = mx + w + 3, my + h + 2
                for lab, gg in (('A', ga), ('B', gb)):
                    print('    --- %s 附近 (x=%d..%d) ---' % (lab, x0c, x1c))
                    for ln in ascii_win(gg, x0c, x1c, y0c, y1c):
                        print('    ' + ln)
                # 裁图放大
                for lab, img in (('A', A), ('B', B)):
                    crop = Image.fromarray(img[max(0, y0c):y1c, max(0, x0c):x1c])
                    crop = crop.resize((crop.width * zoom, crop.height * zoom), Image.NEAREST)
                    p = '%s_%s_%s.png' % (pref, f.replace('.png', ''), lab)
                    crop.save(p)
                    print('    → %s' % p)


if __name__ == '__main__':
    main()
