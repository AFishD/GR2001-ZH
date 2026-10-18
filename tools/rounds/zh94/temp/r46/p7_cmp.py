# -*- coding: utf-8 -*-
r"""p7_cmp.py — 对比 GR_ZH94 / GR_ZH95 的引擎图, 找出"被误清的像素"。"""
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import numpy as np                                     # noqa: E402
import tcslib                                          # noqa: E402
import dump_font                                       # noqa: E402
import repack_font                                     # noqa: E402

A_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH94', 'GR_ZH94.iso')
B_ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH95', 'GR_ZH95.iso')
W, H = 1024, 512


def load(p):
    f = dump_font.load_font(p)
    a = f['atlas']
    A = repack_font.Atlas(a['pak'], a['px_off'], a['px_size'], a['w'], a['h'], a['psm'])
    return f, A


fa, Aa = load(A_ISO)
fb, Ab = load(B_ISO)
print('[seg] A 段=%d  B 段=%d' % (len(Aa.segs), len(Ab.segs)))
print('[seg] A: %s' % Aa.segs)
print('[seg] B: %s' % Ab.segs)
print('[hdr] 容器 48B 包头相同: %s' % (Aa.headers() == Ab.headers()))
print('[px ] 容器前 0x200 字节相同: %s' % (bytes(Aa.cont[:0x200]) == bytes(Ab.cont[:0x200])))

d = np.argwhere(Aa.eng != Ab.eng)
print('[diff] 引擎图不同像素 = %d' % len(d))
if len(d):
    ys = d[:, 0]
    print('       y 范围 %d..%d' % (ys.min(), ys.max()))
    # 按网格行归类
    def row_of(y):
        best = None
        for r in range(25):
            yy = tcslib.GRID_Y0 + 16 * (r + (3 if r >= 12 else 0))
            if yy <= y < yy + 16:
                best = r
        return best
    import collections
    c = collections.Counter(row_of(int(y)) for y in ys)
    print('       按网格行: %s' % sorted(c.items()))
    # 只看 434..450 行
    sel = (d[:, 0] >= 430) & (d[:, 0] <= 452)
    print('[diff] y 430..452 的不同像素 = %d' % int(sel.sum()))
    if sel.any():
        dd = d[sel]
        c2 = collections.Counter((int(y), int(x) // 16) for y, x in dd)
        print('       (y, col) 计数: %s' % sorted(c2.items())[:40])

# 直接看记录矩形 0x9E/0x9F/0xA0/0x92/0xFF 在两张盘上的墨量
print()
print('[rec ] 五个单字节码的记录矩形墨量 (A=ZH94 / B=ZH95):')
for code in (0x92, 0x9E, 0x9F, 0xA0, 0xFF):
    r = None
    for (nm, _fld, rs) in fa['faces']:
        if nm == 'default':
            r = rs[code - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    na = int(Aa.eng[v0:v1, u0:u1].sum())
    nb = int(Ab.eng[v0:v1, u0:u1].sum())
    print('       0x%02X rect=(%d,%d,%d,%d)  A墨=%4d  B墨=%4d' % (code, u0, v0, u1, v1, na, nb))

# 保护掩码是否覆盖那些矩形
protect, rects = repack_font.protect_mask(fa['faces'], W, H)
print()
print('[prot] 记录矩形 %d 条; 覆盖 0x9E 矩形 (16,434,32,450) 的像素数 = %d'
      % (len(rects), int(protect[434:450, 16:32].sum())))
miss = []
for (f, c, u0, v0, u1, v1) in rects:
    if not protect[v0:v1, u0:u1].all():
        miss.append((f, c, u0, v0, u1, v1))
print('[prot] 有矩形没被完全覆盖: %d' % len(miss))
