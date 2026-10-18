# -*- coding: utf-8 -*-
r"""g5_ftmap.py — round49 侦察 (五): FT 记录表的 code → (u0,v0,u1,v1) 全映射 + y=482 带逐格点阵。

要回答的问题: y=482..497 这条带里, x>=448 的那些"看着像干净字形"的东西,
到底有没有任何一个 FT 记录指向它们? (= 引擎会不会画它们?)
"""
import io
import os
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


def main():
    font = dump_font.load_font(ISO)
    am, faces = font['atlas'], font['faces']
    A = repack_font.Atlas(am['pak'], am['px_off'], am['px_size'], am['w'], am['h'], am['psm'])
    ink = A.eng
    cs = tcslib.Charset()
    for (fn, fld, recs) in faces:
        print('=== face %s (nrec=%d)' % (fn, len(recs)))
        if fn == 'huge':
            print('   (huge face 96 条: code 0x20..0x7F)')
            continue
        groups = {}
        for idx, (b0, b1, u0, v0, u1, v1) in enumerate(recs):
            groups.setdefault((v0, u1 - u0, v1 - v0), []).append(idx + 0x20)
        for k in sorted(groups):
            v0, ww, hh = k
            codes = sorted(groups[k])
            print('   v0=%3d 尺寸 %2dx%2d 共 %2d 条: 码 0x%02X..0x%02X 逐个=%s'
                  % (v0, ww, hh, len(codes), codes[0], codes[-1],
                     ' '.join('%02X' % c for c in codes[:40]) + (' …' if len(codes) > 40 else '')))
        # u0 列表 (确认是否 16px 等距)
        for v0 in sorted(set(r[3] for r in recs)):
            us = sorted(set(r[2] for r in recs if r[3] == v0))
            print('   v0=%3d: u0 = %s' % (v0, us[:20] + (['…'] if len(us) > 20 else [])))
    print()
    # y=482 带逐 16px 格: 墨量 + 该格是否被任何 FT 矩形覆盖
    ft = np.zeros((am['h'], am['w']), bool)
    for (_fn, _fld, rs) in faces:
        for (_b0, _b1, u0, v0, u1, v1) in rs:
            if u1 > u0 and v1 > v0:
                ft[v0:v1, u0:u1] = True
    for y0 in (450, 466, 482, 498):
        if y0 + 16 > am['h']:
            continue
        row = []
        for c in range(64):
            x = c * 16
            n = int(ink[y0:y0 + 16, x:x + 16].sum())
            cov = int(ft[y0:y0 + 16, x:x + 16].sum())
            row.append('%s%d' % ('#' if cov else ('*' if n else '.'), min(n, 9)))
        print('y=%3d 逐格 (col0..63): %s' % (y0, ' '.join(row)))
    print('  说明: #=该格被 FT 矩形覆盖(活字形窗) *=有墨但无窗 .=空格; 数字=墨 px 的十位截断')
    print()
    print('=== y=482..497 的 x=448..704 点阵 (人眼) ===')
    for yy in range(482, 498):
        print('   %3d %s' % (yy, ''.join('#' if ink[yy, x] else '.' for x in range(448, 704))))
    print()
    print('=== y=482..497 的 x=0..256 点阵 (对照: 这是被 FT 矩形覆盖的那段) ===')
    for yy in range(482, 498):
        print('   %3d %s' % (yy, ''.join('#' if ink[yy, x] else '.' for x in range(0, 256))))


if __name__ == '__main__':
    main()
