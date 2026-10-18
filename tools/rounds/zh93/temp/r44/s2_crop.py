# -*- coding: utf-8 -*-
r"""s2_crop.py (round44 实验) — 把 release 图集 PNG 的左上角裁出来放大, 看用户到底看到什么。

只读 release 资料包, 产物写 temp/r44/。不改任何盘上数据。
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(p):
    while True:
        if os.path.isfile(os.path.join(p, 'tools', 'text_csv', 'tcslib.py')):
            return p
        q = os.path.dirname(p)
        if q == p:
            raise SystemExit('!! 找不到仓库根')
        p = q


REPO = find_repo(HERE)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from PIL import Image, ImageDraw                                 # noqa: E402

F1 = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font', 'GR_ZH93_font_atlas_1x.png')
F2 = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'release', 'font', 'GR_ZH93_font_atlas.png')

for p in (F1, F2):
    im = Image.open(p)
    print('[png] %s  mode=%s size=%s' % (os.path.basename(p), im.mode, im.size))
    a = im.convert('L')
    # 每 4 行统计墨点数 (前 64 行), 找"每隔 4 行"的视觉来源
    px = a.load()
    w, h = a.size
    scale = 2 if 'atlas.png' in os.path.basename(p) else 1
    print('      每 4 行墨点合计 (源图行单位, 前 24 源行):')
    for y0 in range(0, 24, 4):
        cnt = [sum(1 for x in range(0, 200 * scale) if px[x, (y0 + k) * scale] < 128)
               for k in range(4)]
        print('        y=%2d..%2d: %s' % (y0, y0 + 3, cnt))

# ── 裁图: 左上角 (0,0)-(192,64) 放大 6 倍 ──
im1 = Image.open(F1).convert('L')
crops = [
    ('c_topleft_x0_y0_192x48_z6.png', (0, 0, 192, 48), 6),
    ('c_topleft_x0_y0_512x64_z3.png', (0, 0, 512, 64), 3),
    ('c_left_x0_y0_128x128_z5.png', (0, 0, 128, 128), 5),
]
for name, box, z in crops:
    c = im1.crop(box).resize(((box[2] - box[0]) * z, (box[3] - box[1]) * z), Image.NEAREST)
    c = c.convert('RGB')
    d = ImageDraw.Draw(c)
    # 画源图 16px 网格 (淡红) + 每 4 行淡蓝, 方便对齐判断
    for x in range(box[0], box[2] + 1, 16):
        d.line([(x - box[0]) * z, 0, (x - box[0]) * z, c.size[1]], fill=(255, 160, 160))
    for y in range(box[1], box[3] + 1, 4):
        col = (120, 190, 255) if (y % 16) else (255, 120, 120)
        d.line([0, (y - box[1]) * z, c.size[0], (y - box[1]) * z], fill=col)
    out = os.path.join(HERE, name)
    c.save(out)
    print('[crop] %s  box=%s  zoom=%d  → %s' % (name, box, z, os.path.basename(out)))

# ── 参考: 原版 EN 图集按 8bpp 正规读法的左上角 (自己读盘, 不影响任何人) ──
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
import dump_font                                                  # noqa: E402

font = dump_font.load_font(os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso'))
at = font['atlas']
w, h = at['w'], at['h']
px = at['pak'][at['px_off']:at['px_off'] + w * h]
im = Image.frombytes('L', (w, h), bytes(0 if b == 0 else 255 for b in px))
c = im.crop((0, 0, 192, 48)).resize((192 * 6, 48 * 6), Image.NEAREST).convert('RGB')
d = ImageDraw.Draw(c)
for x in range(0, 193, 16):
    d.line([x * 6, 0, x * 6, c.size[1]], fill=(255, 160, 160))
for y in range(0, 49, 4):
    d.line([0, y * 6, c.size[0], y * 6], fill=(120, 190, 255))
c.save(os.path.join(HERE, 'c_en_orig_8bpp_topleft_192x48_z6.png'))
print('[crop] EN 原版 8bpp 正规读法左上角 → c_en_orig_8bpp_topleft_192x48_z6.png')

# ── Lead 的读法 (把 8bpp 数据当 4bpp 读) 对比 ──
g = dump_font.atlas_gray(at)
im2 = Image.frombytes('L', (w, h), g)
im2.crop((0, 0, 192, 48)).resize((192 * 6, 48 * 6), Image.NEAREST).convert('RGB').save(
    os.path.join(HERE, 'c_en_orig_4bpp_misread_topleft_192x48_z6.png'))
print('[crop] EN 原版「当 4bpp 读」左上角 → c_en_orig_4bpp_misread_topleft_192x48_z6.png')
