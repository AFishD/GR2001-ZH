# -*- coding: utf-8 -*-
r"""p19_rsb_render.py — round42: 试解 GR.IMG#861 PDA_COUNTERPARTS.RSB (262237 B) 的真实布局

已知: 同类 RSB (hanliu/tools/research/oldrsb.py) 的头 = 93 字节, w/h 在 +4/+8。
本文件: ver=6, w=0x100(256), h=0x100(256), 之后 4 个 0x08;
         262237 - 93 = 262144 = 256*256*4 = 512*512*1 —— 两种都刚好填满。
⇒ 两种都渲染出来, 与 COMMON.PAK 里同名记录的 256x256 图对比。
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib                                                    # noqa: E402
from PIL import Image                                            # noqa: E402

iso = tcslib.Iso(os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
e = iso.img_entry(tcslib.GR_LBA, 861)
rsb = iso.read(e['iso_off'], e['stored'])
# COMMON.PAK 里的 CLUT + 像素
pak_e = None
for i in range(24):
    x = iso.img_entry(tcslib.MENU_LBA, i)
    if x['name'] == 'COMMON.PAK':
        pak_e = x
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
        px256 = pak[pxoff + 4: pxoff + 4 + pxsz]
        cl = pak[q + 16:q + 16 + clut]
        break
    base = pxoff + 4 + pxsz
clut = cl[16:16 + 1024]

print('RSB %d B; 头 93 B; 载荷 %d B' % (len(rsb), len(rsb) - 93))
print('头字段: ver=%d w=%d h=%d f=%s'
      % (struct.unpack_from('<I', rsb, 0)[0], struct.unpack_from('<I', rsb, 4)[0],
         struct.unpack_from('<I', rsb, 8)[0],
         struct.unpack_from('<4I', rsb, 12)))
pay = rsb[93:]


def cls(rgb):
    R, G, B = rgb
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


# ── 假设 A: 512x512 8bpp indexed + COMMON.PAK 的 CLUT ──
A = Image.new('RGB', (512, 512))
ap = A.load()
for y in range(512):
    for x in range(512):
        i = pay[y * 512 + x]
        o = i * 4
        ap[x, y] = (clut[o], clut[o + 1], clut[o + 2])
A.save(os.path.join(HERE, 'rsb_A_512x512_8bpp.png'))
print()
print('假设 A: 512x512 8bpp + COMMON.PAK CLUT → rsb_A_512x512_8bpp.png')
print('  行带 y=196..220, x=0..140:')
for y in range(196, 221, 2):
    print('   %3d %s' % (y, ''.join(cls(ap[x, y]) for x in range(0, 140))))

# ── 假设 B: 256x256 RGBA8888 ──
B = Image.new('RGBA', (256, 256))
bp = B.load()
for y in range(256):
    for x in range(256):
        o = (y * 256 + x) * 4
        bp[x, y] = (pay[o], pay[o + 1], pay[o + 2], 255)
bg = Image.new('RGBA', (256, 256), (255, 255, 255, 255))
Image.alpha_composite(bg, B).convert('RGB').save(
    os.path.join(HERE, 'rsb_B_256x256_rgba.png'))
print()
print('假设 B: 256x256 RGBA8888 → rsb_B_256x256_rgba.png')
print('  行带 y=196..220, x=0..140 (用 A 的配色分类):')
for y in range(196, 221, 2):
    print('   %3d %s' % (y, ''.join(cls(bp[x, y][:3]) for x in range(0, 140))))

# ── 假设 C: 512x512 8bpp 但 CLUT 在 RSB 头里 (偏移 0x18) ──
cc = rsb[0x18:0x18 + 1024]
print()
print('假设 C: RSB 头 0x18 起的 1024 B 是否是 CLUT? 前 6 个 32bit: %s'
      % ' '.join('%08X' % struct.unpack_from('<I', cc, i * 4)[0] for i in range(6)))
