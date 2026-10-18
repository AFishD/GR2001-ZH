# -*- coding: utf-8 -*-
r"""p15_box_colors.py — round42: 用**颜色构成**判定每个声明 UV 框里到底是哪个按键图标

图标配色 (实测): ✕=蓝+红, △=蓝, □=紫/粉, ○=红, 空白键=白, "?"=红底白问号, "✓"=红底白勾
背景 = 全图出现最多的颜色索引。
"""
import os
import struct
import sys
from collections import Counter

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


def rgb(i):
    o = i * 4
    return (clut[o], clut[o + 1], clut[o + 2])


def hist(u0, v0, u1, v1):
    c = Counter()
    for y in range(v0, v1):
        for x in range(u0, u1):
            c[rgb(px[y * w + x])] += 1
    return c


BOXES = [('文本图标 0xB5', (1, 198, 21, 218)),
         ('文本图标 0xB1', (25, 198, 45, 218)),
         ('(对照) 49..69', (49, 198, 69, 218)),
         ('(对照) 73..93', (73, 198, 93, 218)),
         ('(对照) 97..117', (97, 198, 117, 218)),
         ('sc 26/28 (0,178)-(20,198)', (0, 178, 20, 198)),
         ('sc 29 (21,178)-(41,198)', (21, 178, 41, 198)),
         ('sc 30 (42,178)-(62,198)', (42, 178, 62, 198)),
         ('sc 31 (63,178)-(83,198)', (63, 178, 83, 198)),
         ('sc 27 (85,178)-(120,198)', (85, 178, 120, 198))]
print('每个声明 UV 框的颜色构成 (只列 >=3%% 的颜色; RGB 是 CLUT 里的实际颜色)')
print('=' * 78)
for name, box in BOXES:
    c = hist(*box)
    tot = sum(c.values())
    top = [(k, v) for k, v in c.most_common() if v * 100.0 / tot >= 3.0][:5]
    print('  %-28s %s' % (name, '  '.join('RGB%s×%d(%.0f%%)' % (k, v, v * 100.0 / tot)
                                          for k, v in top)))
