# -*- coding: utf-8 -*-
r"""p8_zone.py — 把图集左下角 (x 0..270, y 425..460) 打成 ASCII 图, 对比 ZH94/ZH95。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import dump_font                                       # noqa: E402
import repack_font                                     # noqa: E402


def load(p):
    f = dump_font.load_font(p)
    a = f['atlas']
    return repack_font.Atlas(a['pak'], a['px_off'], a['px_size'], a['w'], a['h'], a['psm']), f


A, fa = load(os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso'))
B, fb = load(os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'GR_ZH95.iso'))

X0, X1, Y0, Y1 = 0, 272, 426, 458
print('区域 x %d..%d  y %d..%d   (%s = A有墨 %s = B有墨 %s = 两张都有墨 . = 都空)'
      % (X0, X1 - 1, Y0, Y1 - 1, '#', '*', '%'))
print('     ' + ''.join(str((x // 16) % 10) if x % 16 == 0 else ' ' for x in range(X0, X1)))
for y in range(Y0, Y1):
    row = []
    for x in range(X0, X1):
        a, b = A.eng[y, x], B.eng[y, x]
        row.append('%' if (a and b) else ('#' if a else ('*' if b else '.')))
    mark = ''
    for r in range(25):
        yy = 2 + 16 * (r + (3 if r >= 12 else 0))
        if yy == y:
            mark = ' <== yrow(%d)' % r
    print('%4d %s%s' % (y, ''.join(row), mark))

print()
print('记录矩形与"邻域"里各自有多少墨:')
for code in (0x92, 0x9E, 0x9F, 0xA0, 0xFF):
    r = [x for x in fa['faces'] if x[0] == 'default'][0][2][code - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    w = [(u0, v0, u1, v1), (u0 + 4, v0 + 2, u1 + 4, v1 + 2),
         (u0 - 4, v0 - 2, u1 + 4, v1 + 2)]
    print('  0x%02X rect=(%d,%d,%d,%d)' % (code, u0, v0, u1, v1))
    for k, (a0, b0, a1, b1) in enumerate(w):
        a0, b0 = max(0, a0), max(0, b0)
        a1, b1 = min(1024, a1), min(512, b1)
        print('      窗%d (%4d,%3d)-(%4d,%3d): A墨=%4d  B墨=%4d'
              % (k, a0, b0, a1, b1, int(A.eng[b0:b1, a0:a1].sum()), int(B.eng[b0:b1, a0:a1].sum())))
