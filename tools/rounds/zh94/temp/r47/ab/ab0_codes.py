# -*- coding: utf-8 -*-
r"""ab0_codes.py — 从两盘图集里**派生**受影响的码位表 (只读 ISO)。

· 差异像素 → 落在哪些记录矩形里 → 码位 → 字符 (tcslib.Charset);
· 每格打印 ASCII: 修前(GR_ZH94) / 修后(GR_ZH96_fix) 对照 —— 一眼看出多出来的是哪几个墨点;
· 存 JSON 供后续脚本使用。
"""
import io
import json
import os
import sys

import numpy as np

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HERE = os.path.dirname(os.path.abspath(__file__))
R47 = os.path.abspath(os.path.join(HERE, '..'))
sys.path.insert(0, R47)

import r47lib                                                       # noqa: E402
import tcslib                                                       # noqa: E402


def ascii_cell(img, u0, v0, u1, v1, mark='#'):
    return ['%4d |%s|' % (y, ''.join(mark if img[y, x] < 128 else '.' for x in range(u0, u1 + 1)))
            for y in range(v0, v1 + 1)]


def main():
    A = r47lib.load('GR_ZH94')
    B = r47lib.load('GR_ZH96_fix')
    cs = tcslib.Charset()
    print('图集 1024x512; 记录矩形取自 default face (引擎实际用的那张表)')
    ea, eb = A['eng'], B['eng']
    d = (ea != eb)
    ys, xs = np.where(d)
    print('两盘图集差异: %d 像素; y 取值 = %s; x 范围 = %d..%d'
          % (int(d.sum()), sorted(set(ys.tolist())), int(xs.min()), int(xs.max())))
    ra, rb = r47lib.default_rects(A['faces']), r47lib.default_rects(B['faces'])
    assert ra == rb, '两盘记录矩形表不同!'
    codes = []
    for code in sorted(ra):
        u0, v0, u1, v1 = ra[code]
        n = int(d[v0:v1 + 1, u0:u1 + 1].sum())
        if n:
            codes.append((code, u0, v0, u1, v1, n))
    print('受影响码位 %d 个:' % len(codes))
    print('  码位  字符  记录矩形(u0..u1, v0..v1)   差异像素')
    for (code, u0, v0, u1, v1, n) in codes:
        print('  0x%02X  %s     u=%3d..%3d v=%3d..%3d      %2d'
              % (code, cs.codes.get(code, '?'), u0, u1, v0, v1, n))
    print()
    print('逐格 ASCII 对照 (修前 → 修后; 只印有差异的那些行):')
    for (code, u0, v0, u1, v1, n) in codes:
        ch = cs.codes.get(code, '?')
        cellA = ea[v0:v1 + 1, u0:u1 + 1]
        cellB = eb[v0:v1 + 1, u0:u1 + 1]
        diffrows = [i for i in range(cellA.shape[0]) if (cellA[i] != cellB[i]).any()]
        print()
        print('--- 0x%02X 「%s」 v=%d..%d  差异行(格内相对行号) %s ---'
              % (code, ch, v0, v1, diffrows))
        for lab, img in (('修前', cellA), ('修后', cellB)):
            print('  [%s]' % lab)
            for i in range(img.shape[0]):
                flag = ' <<' if (cellA[i] != cellB[i]).any() else ''
                print('   %2d |%s|%s' % (i, ''.join('#' if img[i, x] < 128 else '.'
                                                   for x in range(img.shape[1])), flag))

    out = dict(texel_diff=int(d.sum()),
               y_values=sorted(set(ys.tolist())),
               codes=[dict(code=c, char=cs.codes.get(c, '?'), u0=u0, v0=v0, u1=u1, v1=v1, n=n)
                      for (c, u0, v0, u1, v1, n) in codes])
    io.open(os.path.join(HERE, 'ab0_codes.json'), 'w', encoding='utf-8',
            newline='\n').write(json.dumps(out, ensure_ascii=False, indent=1) + '\n')
    print()
    print('→ %s' % os.path.join(HERE, 'ab0_codes.json'))


if __name__ == '__main__':
    main()
