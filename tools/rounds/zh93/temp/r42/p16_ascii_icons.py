# -*- coding: utf-8 -*-
r"""p16_ascii_icons.py — round42: 把 pda_counterparts 的图标行画成「颜色分类」ASCII 图, 一眼定位每个按键
类: . = 黑底  W = 白  G = 灰(键帽底)  B = 蓝  R = 红  P = 紫  o = 其它
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402

iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
pak_e = None
for i in range(24):
    e = iso.img_entry(tcslib.MENU_LBA, i)
    if e['name'] == 'COMMON.PAK':
        pak_e = e
        break
pak = iso.read(pak_e['iso_off'], pak_e['stored'])
iso.close()
base = 0
while base + 8 <= len(pak):
    ty, nl = struct.unpack_from('<II', pak, base)
    if ty == 0x63 or nl > 64:
        break
    nm = pak[base + 8:base + 8 + nl].decode('latin-1')
    q = base + 8 + nl
    psm, w, h, clut = struct.unpack_from('<4I', pak, q)
    pxoff = q + 16 + clut
    pxsz = struct.unpack_from('<I', pak, q + 16 + clut)[0]
    if nm == 'pda_counterparts':
        px = pak[pxoff + 4: pxoff + 4 + pxsz]
        cl = pak[q + 16:q + 16 + clut]
        break
    base = pxoff + 4 + pxsz
clut = cl[16:16 + 1024]


def cls(i):
    o = i * 4
    R, G, B = clut[o], clut[o + 1], clut[o + 2]
    if (R, G, B) == (0, 0, 0):
        return '.'
    if R > 200 and G > 200 and B > 200:
        return 'W'
    if R < 120 and G < 120 and B < 120 and abs(R - G) < 20 and abs(G - B) < 20:
        return 'G'
    if B > 150 and B > R + 40:
        return 'B'
    if R > 120 and R > B + 30 and G < 150:
        return 'R'
    if R > 120 and B > 120 and G < R - 20:
        return 'P'
    return 'o'


print('pda_counterparts 图标行 ASCII 颜色图 (x=0..129, y=176..222)')
print('  . 黑底   W 白   G 灰键帽   B 蓝   R 红   P 紫   o 其它')
for band, (v0, v1) in (('── 行带 v=178..198 (快捷键图标) ──', (176, 198)),
                       ('── 行带 v=198..218 (文本图标码用的那行) ──', (198, 220))):
    print()
    print(band)
    print('     ' + ''.join(str((x // 10) % 10) for x in range(0, 130)))
    print('     ' + ''.join(str(x % 10) for x in range(0, 130)))
    for y in range(v0, v1):
        print('  %3d %s' % (y, ''.join(cls(px[y * w + x]) for x in range(0, 130))))
print()
print('=' * 78)
print('引擎声明的 UV 框  vs  图里图标的真实位置')
print('=' * 78)
for label, (u0, v0, u1, v1) in (('文本码 0xB5', (1, 198, 21, 218)),
                                ('文本码 0xB1', (25, 198, 45, 218))):
    from collections import Counter
    c = Counter(cls(px[y * w + x]) for y in range(v0, v1) for x in range(u0, u1))
    print('  %-10s (%3d,%3d)-(%3d,%3d): %s'
          % (label, u0, v0, u1, v1, ' '.join('%s×%d' % kv for kv in c.most_common())))
