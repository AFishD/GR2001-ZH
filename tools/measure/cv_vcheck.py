# -*- coding: utf-8 -*-
r"""cv_vcheck.py v4 — 「日」字形标定盘 垂直偏移检测（低通+二值化, 抗半透明背景干扰）
==============================================================================
方法 (按用户指定: 二值化+低通滤波):
  1. 高斯低通 (5x5, σ1.2) 压噪;
  2. 二值化两极性: 亮墨(高阈值)/暗墨(低阈值) — 半透明叠加层(中灰)被排除;
  3. 墨迹行剖面 → 带; 等距三连带 = 一行字形 (顶框/杠/底框, 杠=格垂直中心);
  4. 长横线 = 显示框/分隔线, 记录其原始灰度 → 分类 opaque(实线)/dim(半透明);
  5. N = 杠中心 − 参考线对中心 (正 = 杠偏上), 分别对 opaque/dim 两类参考输出。
用法: python cv_vcheck.py img1.png [img2.png ...]
输出: 终端表格 + <img>_vchk.png 标注图 + <img>_vchk.json

实测要点 (2026-09-19 定案, 详见 PROGRESS §16):
  · 参考线有两族: 暗线族(半透明, 灰度~40-90) 与 亮线族(不透明, 灰度~180+),
    两族各自等节距(菜单行距: 原生~27.5px / 用户3.2x~86.5px), 互相错开 ~11.5px(≈3.6 原生);
    行槽边框 = 暗线+亮线成对 (border pair), N 应对「边框对中心」计算。
  · 原生 1x 图参数: 不模糊或极轻模糊 + 阈值~140 (1px 线糊后掉到 90-130);
    放大图 (~3.2x): 模糊 σ1.2 + 阈值 105-125。
  · 帮助条文字格 = 全高格 (顶/杠/底三带齐全), 箱边框为暗带 (y±过渡带), 定位取带中心。
"""
import sys, os, json
import cv2
import numpy as np

BLUR_K, BLUR_S = 5, 1.2
BAND_FRAC = 0.22        # 行剖面阈值 (×剖面最大值)
TRIPLET_TOL = 0.30      # 三连带等距容差
LINE_MULT = 2.5         # 长线最小长度 = LINE_MULT × 格宽
OPAQUE_THR = 140        # 线条原始灰度 ≥ 此值 = opaque(实线), 否则 dim(半透明/暗线)


def imread_u(path, flags=cv2.IMREAD_COLOR):
    data = np.fromfile(path, dtype=np.uint8)
    return cv2.imdecode(data, flags)


def imwrite_u(path, img):
    ext = os.path.splitext(path)[1] or '.png'
    ok, buf = cv2.imencode(ext, img)
    if ok:
        buf.tofile(path)
    return ok


def true_runs(a):
    out, cur, n = [], 0, len(a)
    while cur < n:
        if a[cur]:
            s = cur
            while cur < n and a[cur]:
                cur += 1
            out.append((s, cur - s))
        else:
            cur += 1
    return out


def analyze(path):
    gray0 = imread_u(path, cv2.IMREAD_GRAYSCALE)
    if gray0 is None:
        return dict(error='cannot read %s' % path), None
    H, W = gray0.shape
    blur = cv2.GaussianBlur(gray0, (BLUR_K, BLUR_K), BLUR_S)
    masks = []
    for pol, thr in (('bright', 105), ('dark', 70)):
        m = (blur > thr) if pol == 'bright' else (blur < thr)
        if m.sum() < 50 or m.sum() > 0.5 * H * W:
            continue
        masks.append((pol, m.astype(np.uint8)))
    if not masks:
        masks = [('bright', (blur > np.percentile(blur, 92)).astype(np.uint8))]

    bands_all, lines = [], []
    for pol, m in masks:
        prof = m.sum(axis=1).astype(np.float32)
        peak = prof.max()
        if peak < 6:
            continue
        active = prof >= BAND_FRAC * peak
        y = 0
        while y < H:
            if active[y]:
                y0 = y
                while y < H and (active[y] or active[y + 1:y + 3].any()):
                    y += 1
                seg = m[y0:y]
                cols = seg.any(axis=0)
                runs = [r for _, r in true_runs(cols)]
                if runs:
                    bands_all.append(dict(yc=(y0 + y - 1) / 2.0, pol=pol,
                                          longest=float(max(runs)), nruns=len(runs)))
            y += 1
    if not bands_all:
        return dict(image=os.path.basename(path), size=[W, H], error='no bands'), None

    # 字形带 (短) vs 长线: 宽度双簇
    lrs = sorted(b['longest'] for b in bands_all)
    split = None
    for a, b in zip(lrs, lrs[1:]):
        if a >= 10 and b >= 2.2 * a:
            split = (a + b) / 2.0
            break
    if split is None:
        glyph = bands_all
        lines = []
    else:
        glyph = [b for b in bands_all if b['longest'] < split]
        longb = [b for b in bands_all if b['longest'] >= split]
        for b in longb:
            g = float(gray0[int(b['yc']), :][gray0[int(b['yc']), :] > 0].mean()) if (gray0[int(b['yc']), :] > 0).any() else 0.0
            rr = int(max(0, b['yc'] - 1)), int(min(H, b['yc'] + 2))
            rowpix = gray0[rr[0]:rr[1], :].ravel()
            g = float(np.median(rowpix[rowpix > np.percentile(rowpix, 80)])) if True else 0
            b['gray'] = g
            b['cls'] = 'opaque' if g >= OPAQUE_THR else 'dim'
            lines.append(b)

    # 等距三连带
    gs = sorted(glyph, key=lambda b: b['yc'])
    used, rows = set(), []
    for i in range(len(gs) - 2):
        if i in used:
            continue
        for j in range(i + 1, len(gs) - 1):
            if j in used:
                continue
            g1 = gs[j]['yc'] - gs[i]['yc']
            if g1 < 3:
                continue
            for k in range(j + 1, len(gs)):
                if k in used:
                    continue
                g2 = gs[k]['yc'] - gs[j]['yc']
                if abs(g1 - g2) <= TRIPLET_TOL * min(g1, g2):
                    rows.append((gs[i], gs[j], gs[k]))
                    used.update((i, j, k))
                    break
            break

    res = dict(image=os.path.basename(path), size=[W, H],
               lines=[dict(y=round(l['yc'], 1), cls=l.get('cls'), gray=round(l.get('gray', 0), 0),
                           run=round(l['longest'])) for l in lines],
               rows=[])
    lys = [l['yc'] for l in lines]
    for (bt, bb, bo) in rows:
        top, bar, bot = bt['yc'], bb['yc'], bo['yc']
        span = bot - top
        scale = span / 15.0
        rec = dict(y_top=round(top, 1), y_bar=round(bar, 1), y_bot=round(bot, 1),
                   span=round(span, 1), scale=round(scale, 2),
                   bar_dev=round(bar - (top + bot) / 2.0, 2), pol=bb['pol'])
        for cls in ('opaque', 'dim', None):
            cand = [l for l in lines if (cls is None or l.get('cls') == cls)]
            tb = [l['yc'] for l in cand if l['yc'] < top - 1]
            bl = [l['yc'] for l in cand if l['yc'] > bot + 1]
            if tb and bl:
                t_, b_ = max(tb), min(bl)
                n = ((t_ + b_) / 2.0 - bar) / max(scale, 1e-6)
                key = cls or 'any'
                rec['N_' + key] = round(n, 2)
                rec['frame_' + key] = [round(t_, 1), round(b_, 1)]
        res['rows'].append(rec)
    return res, (bands_all, lines, rows)


def annotate(path, res):
    img = imread_u(path)
    for i, r in enumerate(res.get('rows', [])):
        cv2.line(img, (0, int(r['y_top'])), (img.shape[1], int(r['y_top'])), (0, 200, 0), 1)
        cv2.line(img, (0, int(r['y_bar'])), (img.shape[1], int(r['y_bar'])), (255, 255, 0), 2)
        cv2.line(img, (0, int(r['y_bot'])), (img.shape[1], int(r['y_bot'])), (0, 200, 0), 1)
        lbl = 'r%d s=%.2f bardev=%+.1f' % (i, r['scale'], r['bar_dev'])
        for k in ('N_opaque', 'N_dim', 'N_any'):
            if k in r:
                lbl += ' %s=%+.2f' % (k, r[k])
        cv2.putText(img, lbl, (8, int(r['y_top']) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        cv2.putText(img, lbl, (8, int(r['y_top']) - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    for l in res.get('lines', []):
        col = (255, 0, 255) if l['cls'] == 'opaque' else (180, 120, 255)
        cv2.line(img, (0, int(l['y'])), (img.shape[1], int(l['y'])), col, 1)
    out = os.path.splitext(path)[0] + '_vchk.png'
    imwrite_u(out, img)
    return out


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    for p in sys.argv[1:]:
        r, _ = analyze(p)
        if 'error' in r:
            print(p, 'ERROR:', r.get('error'))
            continue
        ann = annotate(p, r)
        print('=' * 100)
        print('%s size=%s' % (r['image'], r['size']))
        print(' lines: ' + '; '.join('y=%s %s(g%d,run%d)' % (l['y'], l['cls'], l['gray'], l['run'])
                                     for l in r['lines']))
        print('%-3s %-7s %-7s %-7s %-5s %-5s %-7s | %-9s %-9s %-9s' %
              ('row', 'y_top', 'y_bar', 'y_bot', 's', 'bdev', 'pol', 'N_opaque', 'N_dim', 'N_any'))
        for i, b in enumerate(r['rows']):
            print('%-3d %-7s %-7s %-7s %-5s %-5s %-7s | %-9s %-9s %-9s' %
                  (i, b['y_top'], b['y_bar'], b['y_bot'], b['scale'], b['bar_dev'], b['pol'],
                   b.get('N_opaque', '-'), b.get('N_dim', '-'), b.get('N_any', '-')))
        json.dump(r, open(os.path.splitext(p)[0] + '_vchk.json', 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(' annotated ->', ann)
