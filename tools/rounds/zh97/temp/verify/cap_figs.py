# -*- coding: utf-8 -*-
r"""cap_figs.py — 由两轮抓帧生成"同帧放大对照图"(按**差异簇**分格, 不把整列并成一张巨图)。

用法:
  # ① 自动: 对指定帧按差异簇出图 (左=修前 A / 中=修后 B / 右=差异)
  python cap_figs.py <dirA> <dirB> --frames snap_f00001900.png,snap_f00006000.png \
         --outdir figs [--zoom 12] [--pad 8]

  # ② 手动: 指定裁剪框 (做"主菜单五行全景"这种上下文图)
  python cap_figs.py <dirA> <dirB> --frames snap_f00006000.png \
         --rect 40,120,330,240 --outdir figs --zoom 4 --name menu_wide

差异簇 = 差异像素按 (相邻 2 行内 & x 间隔 ≤ gap) 聚成一块。
"""
import io
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))


def clusters(ys, xs, gap=10):
    pts = sorted(zip(ys.tolist(), xs.tolist()))
    out = []
    for y, x in pts:
        for c in out:
            if y <= c['y1'] + 2 and x >= c['x0'] - gap and x <= c['x1'] + gap:
                c['y0'] = min(c['y0'], y); c['y1'] = max(c['y1'], y)
                c['x0'] = min(c['x0'], x); c['x1'] = max(c['x1'], x)
                c['n'] += 1
                break
        else:
            out.append(dict(y0=y, y1=y, x0=x, x1=x, n=1))
    # 合并第二轮 (可能互相连上)
    changed = True
    while changed:
        changed = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a, b = out[i], out[j]
                if (a['y0'] <= b['y1'] + 2 and b['y0'] <= a['y1'] + 2
                        and a['x0'] <= b['x1'] + gap and b['x0'] <= a['x1'] + gap):
                    a['y0'] = min(a['y0'], b['y0']); a['y1'] = max(a['y1'], b['y1'])
                    a['x0'] = min(a['x0'], b['x0']); a['x1'] = max(a['x1'], b['x1'])
                    a['n'] += b['n']
                    out.pop(j)
                    changed = True
                    break
            if changed:
                break
    return out


def panel(ia, ib, box, label, zoom, pad, la, lb):
    W, H = ia.size
    x0 = max(0, box[0] - pad); y0 = max(0, box[1] - pad)
    x1 = min(W, box[2] + 1 + pad); y1 = min(H, box[3] + 1 + pad)
    ca, cb = ia.crop((x0, y0, x1, y1)), ib.crop((x0, y0, x1, y1))
    aa, bb = np.asarray(ca), np.asarray(cb)
    d = np.any(aa != bb, axis=2)
    cd = bb.copy()
    cd[d] = (255, 40, 40)
    w, h = ca.size
    zw, zh = w * zoom, h * zoom
    aa2 = ca.resize((zw, zh), Image.NEAREST)
    bb2 = cb.resize((zw, zh), Image.NEAREST)
    dd2 = Image.fromarray(cd).resize((zw, zh), Image.NEAREST)
    bar = 30
    out = Image.new('RGB', (zw * 3 + 8, zh + bar), (14, 14, 14))
    dr = ImageDraw.Draw(out)
    dr.text((4, 3), label, fill=(255, 255, 0))
    dr.text((4, 15), la, fill=(190, 215, 255))
    dr.text((zw + 12, 15), lb, fill=(195, 255, 195))
    dr.text((zw * 2 + 20, 15), 'DIFF  红 = 差异像素 (%d)' % int(d.sum()), fill=(255, 165, 165))
    out.paste(aa2, (0, bar)); out.paste(bb2, (zw + 4, bar)); out.paste(dd2, (zw * 2 + 8, bar))
    return out


def main():
    a = sys.argv[1:]
    da, db = a[0], a[1]
    fr = a[a.index('--frames') + 1].split(',')
    outdir = a[a.index('--outdir') + 1] if '--outdir' in a else os.path.join(HERE, 'figs')
    zoom = int(a[a.index('--zoom') + 1]) if '--zoom' in a else 12
    pad = int(a[a.index('--pad') + 1]) if '--pad' in a else 8
    rect = a[a.index('--rect') + 1] if '--rect' in a else None
    name = a[a.index('--name') + 1] if '--name' in a else None
    la = a[a.index('--label-a') + 1] if '--label-a' in a else 'A 修前 (GR_ZH95)'
    lb = a[a.index('--label-b') + 1] if '--label-b' in a else 'B 修后 (GR_ZH97)'
    os.makedirs(outdir, exist_ok=True)
    for fn in fr:
        ia = Image.open(os.path.join(da, fn)).convert('RGB')
        ib = Image.open(os.path.join(db, fn)).convert('RGB')
        if rect:
            x0, y0, x1, y1 = [int(v) for v in rect.split(',')]
            p = panel(ia, ib, (x0, y0, x1, y1),
                      '%s  crop %s' % (fn, rect), zoom, pad, la, lb)
            op = os.path.join(outdir, 'fig_%s.png' % (name or os.path.splitext(fn)[0]))
            p.save(op)
            print('  %s → %s (%dx%d)' % (fn, op, p.size[0], p.size[1]))
            continue
        aa, bb = np.asarray(ia), np.asarray(ib)
        d = np.any(aa != bb, axis=2)
        ys, xs = np.where(d)
        if not len(ys):
            print('  %s 无差异, 跳过' % fn)
            continue
        cls = clusters(ys, xs)
        cls.sort(key=lambda c: (c['y0'], c['x0']))
        print('  %s: %d 个差异簇, 合计 %d px' % (fn, len(cls), int(d.sum())))
        parts = []
        for i, c in enumerate(cls, 1):
            lab = '%s  簇%d/%d  x=%d..%d y=%d..%d (%dx%d)  %d px' % (
                fn, i, len(cls), c['x0'], c['x1'], c['y0'], c['y1'],
                c['x1'] - c['x0'] + 1, c['y1'] - c['y0'] + 1, c['n'])
            parts.append(panel(ia, ib, (c['x0'], c['y0'], c['x1'], c['y1']),
                               lab, zoom, pad, la, lb))
        Wt = max(p.size[0] for p in parts)
        Ht = sum(p.size[1] + 10 for p in parts)
        stack = Image.new('RGB', (Wt, Ht), (30, 30, 30))
        yy = 0
        for p in parts:
            stack.paste(p, (0, yy)); yy += p.size[1] + 10
        op = os.path.join(outdir, 'fig_%s.png' % os.path.splitext(fn)[0])
        stack.save(op)
        print('       → %s (%dx%d)' % (op, stack.size[0], stack.size[1]))


if __name__ == '__main__':
    main()
