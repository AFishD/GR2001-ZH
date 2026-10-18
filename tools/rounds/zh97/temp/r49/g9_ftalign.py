# -*- coding: utf-8 -*-
r"""g9_ftalign.py — 判定 FT 记录矩形的真实采样窗: **原矩形** 还是 **矩形+(4,2)**?

做法 (不需要反汇编, 只看盘上墨的落点):
  · 取 ASCII 带 (v0=452, 每条 8x16) 与单字节带 (v0=482, 每条 16x16) 的若干条;
  · 打印 rect 与 rect+(4,2) 两个窗口里的墨点图案;
  · 统计"墨的包围盒"相对 rect 的偏移分布 (若绝大多数墨落在 rect 内偏左, 窗口=rect;
    若墨整体右移 4px / 下移 2px, 窗口=rect+(4,2))。
另外对**窄条** (8x16 的 ASCII): 用左右各半的墨量比做判据 —— 若墨 8 成以上在右半, 就是右移。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                   # noqa: E402
import tcslib                                                        # noqa: E402
import dump_font                                                     # noqa: E402
import repack_font                                                   # noqa: E402

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH97', 'GR_ZH97.iso')
DU, DV = tcslib.GLYPH_DU, tcslib.GLYPH_DV


def show(ink, x0, y0, w, h, label):
    print('  %s  (%d,%d) %dx%d' % (label, x0, y0, w, h))
    for y in range(y0, y0 + h):
        print('     %s' % ''.join('#' if ink[y, x] else '.' for x in range(x0, x0 + w)))


def main():
    font = dump_font.load_font(ISO)
    am, faces = font['atlas'], font['faces']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    ink = A.eng
    rs = dict((n, r) for (n, _f, r) in faces)['default']
    print('=== A. ASCII 带 (v0=452, 8x16): 墨在 rect 里的横向分布 ===')
    left = right = 0
    per = []
    for idx, (b0, b1, u0, v0, u1, v1) in enumerate(rs):
        if v0 != 452 or u1 - u0 != 8:
            continue
        cell = ink[v0:v1, u0:u1]
        l = int(cell[:, :4].sum())
        r = int(cell[:, 4:].sum())
        left += l
        right += r
        per.append((idx + 0x20, l, r, int(cell.sum())))
    print('  92 条合计: 左半(0..3 列) %d px, 右半(4..7 列) %d px ⇒ 右/左 = %.2f'
          % (left, right, right / max(1, left)))
    print('  (若窗口=rect ⇒ 墨应该左右都有, 大致均衡或偏左; 若窗口=rect+(4,2) ⇒ 墨整体右移 4px,')
    print('   那么 rect 的**左 4 列**基本是空的, 右 4 列才有墨 ⇒ 右/左 会很大)')
    for (c, l, r, t) in per[:8]:
        print('    码 0x%02X: 左 %2d / 右 %2d (共 %d)' % (c, l, r, t))
    print('')
    print('=== B. 逐条"墨包围盒相对 rect"的偏移 (default face, 全部 16x16 条) ===')
    dxs, dys = {}, {}
    for idx, (b0, b1, u0, v0, u1, v1) in enumerate(rs):
        if u1 - u0 != 16 or v1 - v0 != 16:
            continue
        cell = ink[v0:v1, u0:u1]
        ys, xs = np.where(cell)
        if not len(xs):
            continue
        dxs[int(xs.min())] = dxs.get(int(xs.min()), 0) + 1
        dys[int(ys.min())] = dys.get(int(ys.min()), 0) + 1
    print('  墨左边界相对 rect 左边 的分布 (列偏移→条数): %s' % dict(sorted(dxs.items())))
    print('  墨上边界相对 rect 上边 的分布 (行偏移→条数): %s' % dict(sorted(dys.items())))
    print('')
    print('=== C. 看两条实例 ===')
    for code in (0x41, 0x67):
        idx = code - 0x20
        b0, b1, u0, v0, u1, v1 = rs[idx]
        print('  --- 码 0x%02X  rect=(%d,%d)-(%d,%d)' % (code, u0, v0, u1, v1))
        show(ink, u0, v0, u1 - u0, v1 - v0, 'rect 内')
        show(ink, u0 + DU, v0 + DV, u1 - u0, v1 - v0, 'rect+(4,2) 内')
    print('')
    print('=== D. 单字节带 v0=482 的 16x16 条: 墨是否顶到 rect 的上/左边界 ===')
    n_touch_top = n_touch_left = n = 0
    for idx, (b0, b1, u0, v0, u1, v1) in enumerate(rs):
        if v0 != 482:
            continue
        n += 1
        cell = ink[v0:v1, u0:u1]
        if cell[0].any():
            n_touch_top += 1
        if cell[:, 0].any():
            n_touch_left += 1
    print('  %d 条里: 第 0 行有墨 %d 条; 第 0 列有墨 %d 条' % (n, n_touch_top, n_touch_left))
    print('  (若窗口=rect+(4,2), 则字形写在 (u0+4,v0+2) ⇒ rect 第 0/1 行与第 0..3 列应当**都没有墨**)')


if __name__ == '__main__':
    main()
