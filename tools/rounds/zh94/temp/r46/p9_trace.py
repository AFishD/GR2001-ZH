# -*- coding: utf-8 -*-
r"""p9_trace.py — 追查 7 个"底部单字节码"(0x92/0x9D/0x9E/0x9F/0xA0/0xAE/0xFF) 的字形到底在哪。

对比 GR_ZH93 / GR_ZH94 / GR_ZH95 三张盘的**引擎图**与**flat 容器图**在记录矩形里的墨量。
"""
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

ISOS = [('ZH93', 'GR_ZH93'), ('ZH94', 'GR_ZH94'), ('ZH95', 'GR_ZH95')]
CODES = (0x92, 0x9D, 0x9E, 0x9F, 0xA0, 0xAE, 0xFF)
CH = {0x92: '若', 0x9D: '纤', 0x9E: '终', 0x9F: '脆', 0xA0: '膛', 0xAE: '荐', 0xFF: '著'}

loaded = {}
for tag, ver in ISOS:
    p = os.path.join(REPO, 'work', 'builds', ver, ver + '.iso')
    if not os.path.isfile(p):
        continue
    f = dump_font.load_font(p)
    a = f['atlas']
    A = repack_font.Atlas(a['pak'], a['px_off'], a['px_size'], a['w'], a['h'], a['psm'])
    loaded[tag] = (A, f)
    print('[%s] 引擎墨=%d' % (tag, int(A.eng.sum())))

# 记录矩形 (default face)
faces = loaded['ZH94'][1]['faces']
recs = [x for x in faces if x[0] == 'default'][0][2]
print()
print('%-6s %-4s %-26s %8s %8s %8s   %8s %8s %8s' %
      ('code', 'char', 'rect(u0,v0,u1,v1)', 'ZH93eng', 'ZH94eng', 'ZH95eng',
       'ZH93flat', 'ZH94flat', 'ZH95flat'))
for code in CODES:
    r = recs[code - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    row = []
    for tag, _v in ISOS:
        if tag not in loaded:
            row.append(None)
            continue
        A = loaded[tag][0]
        row.append(int(A.eng[v0:v1, u0:u1].sum()))
    # flat 口径: 整个容器当裸图 (旧口径)
    flatn = []
    for tag, _v in ISOS:
        if tag not in loaded:
            flatn.append(None)
            continue
        A = loaded[tag][0]
        stride = A.w // 2
        img = np.zeros((A.h, A.w), dtype=bool)
        n = min(len(A.cont) // stride, A.h)
        a = np.frombuffer(bytes(A.cont[:n * stride]), dtype=np.uint8).reshape(n, stride)
        img[:n, 0::2] = (a & 0x0F) == 0
        img[:n, 1::2] = (a >> 4) == 0
        flatn.append(int(img[v0:v1, u0:u1].sum()))
    print('0x%02X   %-4s (%4d,%4d,%4d,%4d)          %8s %8s %8s   %8s %8s %8s'
          % (code, CH[code], u0, v0, u1, v1,
             *[('-' if x is None else x) for x in row],
             *[('-' if x is None else x) for x in flatn]))

# 这些字形的墨在引擎图里的**真实位置**: 在 ZH94 里找 16x16 全墨块附近
print()
print('ZH94 引擎图里 row24 各 col 的墨量 (y=434..450):')
A = loaded['ZH94'][0]
print('   ' + ' '.join('%2d:%-3d' % (c, int(A.eng[434:450, c * 16:(c + 1) * 16].sum()))
                       for c in range(0, 16)))
print('ZH93 引擎图里 row24 各 col 的墨量 (y=434..450):')
A93 = loaded['ZH93'][0]
print('   ' + ' '.join('%2d:%-3d' % (c, int(A93.eng[434:450, c * 16:(c + 1) * 16].sum()))
                       for c in range(0, 16)))

# ZH93 vs ZH94: row24 带上有哪些列被改过
d = np.argwhere(A93.eng[434:450] != A.eng[434:450])
print()
print('ZH93→ZH94 在 row24 (y434..450) 不同的像素 = %d' % len(d))
if len(d):
    import collections
    print('   按列: %s' % sorted(collections.Counter(int(x) // 16 for _y, x in d).items()))

# 在 ZH93 的引擎图里, 记录矩形窗口的墨量
print()
print('ZH93 记录矩形 3 窗墨量:')
for code in CODES:
    r = recs[code - 0x20]
    u0, v0, u1, v1 = r[2], r[3], r[4], r[5]
    w = [(u0, v0, u1, v1), (u0 + 4, v0 + 2, u1 + 4, v1 + 2), (u0 - 4, v0 - 2, u1 + 4, v1 + 2)]
    print('  0x%02X %s: %s' % (code, CH[code],
                               ' '.join('%d' % int(A93.eng[max(0, b0):b1, max(0, a0):a1].sum())
                                        for (a0, b0, a1, b1) in w)))
