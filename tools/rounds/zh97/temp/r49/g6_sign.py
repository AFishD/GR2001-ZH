# -*- coding: utf-8 -*-
r"""g6_sign.py — 校验 find_copies 的 (dx,dy) 符号约定 (合成图, 不碰真盘)。"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import numpy as np                                                   # noqa: E402
import font_residue as FR                                            # noqa: E402


def main():
    h, w = 64, 128
    ink = np.zeros((h, w), bool)
    # 在 (10, 20) 放一个 8x8 的图案, 并在 (50, 41) 放它的副本 (dx=+40, dy=+21)
    pat = np.zeros((8, 8), bool)
    pat[1, 1] = pat[2, 2] = pat[3, 3] = pat[0, 7] = pat[7, 0] = True
    pat[4, 4] = pat[5, 1] = pat[6, 6] = pat[1, 6] = True
    ink[20:28, 10:18] = pat
    ink[41:49, 50:58] = pat
    out = FR.find_copies(ink, [('src', 10, 20, 18, 28)], w, h, topn=3)
    for e in out:
        print('box=%s ink=%d' % (e['box'], e['ink_px']))
        for hh in e['hits']:
            print('   (dx,dy)=(%+d,%+d) corr=%d' % (hh['dx'], hh['dy'], hh['corr']))
    print('')
    print('期望: 副本在 (x+40, y+21) ⇒ 若约定是"k 平移 (dx,dy) 后落在副本处",')
    print('      则应看到 (dx,dy)=(+40,+21); 若约定相反则是 (-40,-21)。')


if __name__ == '__main__':
    main()
