# -*- coding: utf-8 -*-
r"""g2_probe.py — round49 侦察 (二): 把"可疑残墨"逐像素摊开, 决定能不能清。

问题清单:
  A. 空槽里有墨、FT 矩形外也有墨的那 10 格 (行 21/22 col 5..8, 行 23 col 8/9):
     墨的包围盒在哪? 是否落在 FT 矩形 ± (GLYPH_TOL) 之内 (= 采样邻域)?
  B. 右侧 x=992..1023 那 2073 个墨点: 穷举**全部**采样窗 (1504 对偶格 + 全部 FT 矩形
     ∪ 矩形+(4,2) ∪ 矩形±(4,2)) 后, 还有没有一个墨点落在任何窗内?
  C. y=481..498 那条 (ASCII 第二带): 墨有多少落在 FT 矩形内 / 矩形+(4,2) 内 / 膨胀内?
  D. 空洞带 y=194..241 / 顶部 y=0..1: 确认无采样窗覆盖。
  E. view 表里 has_cjk=yes 的 4 个字 (位吉填菜) 出现在哪些容器/条目。
"""
import csv
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402
import repack_font                                                   # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
TEXT = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'text')
W, H = 1024, 512
DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV
TX, TY = tcslib.GLYPH_TOL_X, tcslib.GLYPH_TOL_Y


def load():
    font = dump_font.load_font(ISO)
    am, faces = font['atlas'], font['faces']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    cs = tcslib.Charset()
    return font, faces, A, cs


def masks(faces):
    """返回 (raw, plus, dil) 三个布尔掩码: 原矩形 / 矩形+(4,2) / 矩形±(4,2)。"""
    raw = np.zeros((H, W), bool)
    plus = np.zeros((H, W), bool)
    dil = np.zeros((H, W), bool)
    rects = []
    for (fn, fld, rs) in faces:
        for idx, r in enumerate(rs):
            _b0, _b1, u0, v0, u1, v1 = r
            if u1 <= u0 or v1 <= v0:
                continue
            rects.append(dict(face=fn, code=idx + 0x20, u0=u0, v0=v0, u1=u1, v1=v1))
            def put(m, a0, b0, a1, b1):
                a0, b0 = max(0, a0), max(0, b0)
                a1, b1 = min(W, a1), min(H, b1)
                if a0 < a1 and b0 < b1:
                    m[b0:b1, a0:a1] = True
            put(raw, u0, v0, u1, v1)
            put(plus, u0, v0, u1, v1)
            put(plus, u0 + DU, v0 + DV, u1 + DU, v1 + DV)
            put(dil, u0 - TX, v0 - TY, u1 + TX, v1 + TY)
    return raw, plus, dil, rects


def main():
    font, faces, A, cs = load()
    ink = A.eng
    raw, plus, dil, rects = masks(faces)
    print('FT 矩形 %d 条; u 范围 %d..%d; v 范围 %d..%d'
          % (len(rects), min(r['u0'] for r in rects), max(r['u1'] for r in rects),
             min(r['v0'] for r in rects), max(r['v1'] for r in rects)))
    print('掩码覆盖: 原矩形 %d, +(%d,%d) %d, 膨胀±(%d,%d) %d'
          % (int(raw.sum()), DU, DV, int(plus.sum()), TX, TY, int(dil.sum())))

    # ---- 全部对偶格掩码 (1504 个, 不管 charset 用没用) ----
    pair = np.zeros((H, W), bool)
    for s in range(tcslib.pair_capacity()):
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        pair[y:y + 16, x:x + 16] = True
    print('1504 个对偶格覆盖 %d px (x<992 的一整条) ' % int(pair.sum()))

    # ---- A. 那 10 格 ----
    print('\n=== A. 空槽有墨 + FT 矩形外有墨的格 ===')
    for (r, c) in [(21, 5), (21, 6), (21, 7), (21, 8), (22, 5), (22, 6), (22, 7), (22, 8),
                   (23, 8), (23, 9)]:
        s = r * tcslib.NCOL + c
        x, y = tcslib.atlas_cell_xy_engine_view(s)
        cell = ink[y:y + 16, x:x + 16]
        ys, xs = np.where(cell)
        bbox = (x + int(xs.min()), y + int(ys.min()), x + int(xs.max()), y + int(ys.max())) \
            if len(xs) else None
        nr = [q for q in rects if q['u0'] < x + 16 and x < q['u1'] and q['v0'] < y + 16 and y < q['v1']]
        nplus = int((cell & plus[y:y + 16, x:x + 16]).sum())
        ndil = int((cell & dil[y:y + 16, x:x + 16]).sum())
        print('  row%2d col%2d slot=%4d 引擎格=(%d,%d) 墨=%3d bbox=%s' % (r, c, s, x, y, int(cell.sum()), bbox))
        print('        墨在 原矩形内 %3d / +(4,2)内 %3d / 膨胀内 %3d  ⇒ 膨胀外还有 %d'
              % (int((cell & raw[y:y + 16, x:x + 16]).sum()), nplus, ndil,
                 int(cell.sum()) - ndil))
        print('        交叠的 FT 矩形: %s'
              % [(q['face'], '0x%02X' % q['code'], q['u0'], q['v0'], q['u1'], q['v1']) for q in nr][:6])

    # ---- B. 右侧两格 ----
    print('\n=== B. x=992..1023 的墨 vs 全部采样窗 ===')
    strip = np.zeros((H, W), bool)
    strip[:, 992:1024] = True
    for nm, m in (('原矩形', raw), ('矩形+(4,2)', plus), ('膨胀±(4,2)', dil)):
        n = int((ink & strip & m).sum())
        print('  落在 x>=992 且属 %s 的墨 = %d' % (nm, n))
    # 也测 x>=992 是否被任何 FT 矩形的 u1 触及
    touch = [q for q in rects if q['u1'] + DU > 992 or q['u1'] + TX > 992]
    print('  u1+(4,2) 或 u1+4 会碰到 x>=992 的矩形: %d 条' % len(touch))
    for q in touch[:10]:
        print('    %s 0x%02X (%d,%d)-(%d,%d)' % (q['face'], q['code'], q['u0'], q['v0'], q['u1'], q['v1']))
    # 逐行给出"墨 & 非膨胀"的位置
    rest = ink & strip & ~dil
    print('  x>=992 且不在任何膨胀窗内的墨 = %d' % int(rest.sum()))
    if rest.any():
        ys, xs = np.where(rest)
        print('    y 范围 %d..%d; 逐行: %s' % (ys.min(), ys.max(),
              {int(y): int((rest[y]).sum()) for y in sorted(set(ys.tolist()))}))

    # ---- C. ASCII 第二带 ----
    print('\n=== C. y=481..498 (FT v0=482 那一条) ===')
    band = np.zeros((H, W), bool)
    band[481:499, :] = True
    for nm, m in (('原矩形', raw), ('矩形+(4,2)', plus), ('膨胀±(4,2)', dil)):
        print('  带内墨 %d, 属 %s 的 %d' % (int((ink & band).sum()), nm, int((ink & band & m).sum())))
    print('  带内不在膨胀窗内的墨 = %d' % int((ink & band & ~dil).sum()))
    q482 = sorted([q for q in rects if q['v0'] == 482], key=lambda q: q['u0'])
    print('  v0=482 的矩形 u0 列表 (每 face): %s'
          % sorted(set((q['face'], q['u0'], q['u1']) for q in q482), key=lambda t: (t[0], t[1]))[:12])
    # 逐 (v0) 组: 墨是否都被膨胀覆盖
    print('\n=== C2. 每个 v0 组: 该 y 带内的墨 / 膨胀内墨 ===')
    for v0 in sorted(set(q['v0'] for q in rects)):
        grp = [q for q in rects if q['v0'] == v0]
        y0, y1 = v0, max(q['v1'] for q in grp)
        m = np.zeros((H, W), bool)
        m[y0:y1, :] = True
        print('  v0=%3d (%d 条, y %d..%d): 墨 %5d, 膨胀内 %5d, 膨胀外 %5d'
              % (v0, len(grp), y0, y1, int((ink & m).sum()), int((ink & m & dil).sum()),
                 int((ink & m & ~dil).sum())))

    # ---- D. 空洞/顶部 ----
    print('\n=== D. 网格外空洞 ===')
    for nm, y0, y1 in (('顶部 y=0..1', 0, 2), ('空洞 y=194..241', 194, 242)):
        m = np.zeros((H, W), bool)
        m[y0:y1, :] = True
        print('  %-20s 墨 %4d, 膨胀内 %d, 膨胀外 %d' % (nm, int((ink & m).sum()),
              int((ink & m & dil).sum()), int((ink & m & ~dil).sum())))

    # ---- E. view 表里的真中文 ----
    print('\n=== E. view 表 has_cjk=yes 的行 (含 位吉填菜) ===')
    for fn in sorted(os.listdir(TEXT)):
        if '_view_' not in fn or not fn.endswith('.csv') or fn.endswith('containers_summary.csv'):
            continue
        with io.open(os.path.join(TEXT, fn), encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                if (row.get('has_cjk') or '').strip().lower() != 'yes':
                    continue
                t = row.get('text') or ''
                if any(ch in t for ch in '位吉填菜'):
                    print('  %-34s %-28s off=%-8s %r'
                          % (fn.replace('GR_ZH97_view_', ''), (row.get('container') or '')[:28],
                             row.get('offset'), t[:60]))


if __name__ == '__main__':
    main()
