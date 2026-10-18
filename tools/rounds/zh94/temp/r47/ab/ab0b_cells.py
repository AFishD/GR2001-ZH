# -*- coding: utf-8 -*-
r"""ab0b_cells.py — 用**正确极性**(字形=亮)打印 20 个受影响格的 ASCII 对照, 并量化残墨。

只读。回答两件事:
  1. 「残墨」到底长什么样 (每个格第 15 行多出来的亮点);
  2. 「斗」(0xD8) 那格在修前是不是看起来像「抖」。
"""
import io
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, '..')))

import r47lib                                                       # noqa: E402
import tcslib                                                       # noqa: E402


def cell_ascii(img, u0, v0, u1, v1):
    """字形=亮(#): 图集里笔画是亮的, 背景暗。"""
    return ['%4d |%s|' % (y, ''.join('#' if img[y, x] >= 128 else '.' for x in range(u0, u1 + 1)))
            for y in range(v0, v1 + 1)]


def main():
    codes = json.load(io.open(os.path.join(HERE, 'ab0_codes.json'), encoding='utf-8'))['codes']
    A = r47lib.load('GR_ZH94')
    B = r47lib.load('GR_ZH96_fix')
    cs = tcslib.Charset()
    ea, eb = A['eng'], B['eng']
    for c in codes:
        code, ch = c['code'], c['char']
        u0, v0, u1, v1 = c['u0'], c['v0'], c['u1'], c['v1']
        ca = ea[v0:v1 + 1, u0:u1 + 1]
        cb = eb[v0:v1 + 1, u0:u1 + 1]
        d = (ca != cb)
        rows = sorted(set(int(y) for y in np.where(d)[0]))
        print('=' * 84)
        print('0x%02X 「%s」 记录矩形 u=%d..%d v=%d..%d  差异 %d 像素, 相对行 %s (=y %s)'
              % (code, ch, u0, u1, v0, v1, int(d.sum()), rows,
                 [v0 + r for r in rows]))
        for lab, img, other in (('修前 GR_ZH94', ca, cb), ('修后 GR_ZH96_fix', cb, ca)):
            print('  [%s]' % lab)
            for i, ln in enumerate(cell_ascii(img, 0, 0, img.shape[1] - 1, img.shape[0] - 1)):
                yy = v0 + i
                mark = ''
                if (img[i] != other[i]).any():
                    ix = [x for x in range(img.shape[1]) if img[i, x] != other[i, x]]
                    mark = '   <<< 差异列 %s' % ix
                print('   %s%s' % (ln, mark))
        print()


if __name__ == '__main__':
    main()
