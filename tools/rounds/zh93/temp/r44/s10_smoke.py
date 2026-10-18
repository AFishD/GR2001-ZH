# -*- coding: utf-8 -*-
r"""s10_smoke.py — 改动后冒烟自检 (只读):
  ① tcslib 新函数可用 & 与旧函数的换算关系自洽;
  ② 现有 GlyphCache (字库预检) 行为未变 (数字与改动前一致);
  ③ 新 dump 的 EN 原版图裁一张出来看 (确认 8bpp 读法真的修好了)。
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
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from PIL import Image                                                 # noqa: E402
import tcslib                                                         # noqa: E402
import dump_font                                                      # noqa: E402

ok = True


def chk(name, cond, extra=''):
    global ok
    ok = ok and bool(cond)
    print('  [%s] %s %s' % ('OK' if cond else '**FAIL**', name, extra))


print('[1] tcslib 新函数')
zh = os.path.join(REPO, 'work', 'builds', 'GR_ZH93', 'GR_ZH93.iso')
en = os.path.join(REPO, 'work', 'builds', 'GR_EN_ORIG', 'GR_EN_ORIG.iso')
fz = dump_font.load_font(zh)
fe = dump_font.load_font(en)
bz = dump_font.container_blob(fz['atlas'])
be = dump_font.container_blob(fe['atlas'])
sz = tcslib.atlas_container_segments(bz, 512)
se = tcslib.atlas_container_segments(be, 512)
chk('ZH 容器解析出 9 段', sz and len(sz) == 9, '首行=%s' % [s[0] for s in sz])
chk('EN 容器解析出 1 段(首行 0)', se and len(se) == 1 and se[0][0] == 0 and se[0][1] == 16,
    '%s' % se)
# 内容不变量: 引擎口径像素 (x,y) 在 flat 视图里位于 atlas_flat_pos(x,y) (s4 §A 的字节级结论)
nz = dump_font.pixels_engine_order(fz['atlas'])[0]
raw_flat = dump_font.container_blob(fz['atlas'])
eng = dump_font.decode_pixels(nz, 1024, 512, 0x14)
flat = dump_font.decode_pixels(raw_flat[:512 * 512], 1024, 512, 0x14)
import random                                                          # noqa: E402
random.seed(44)
bad = 0
for _ in range(4000):
    y = random.randrange(0, 500)
    x = random.randrange(0, 1024)
    x2, y2 = tcslib.atlas_flat_pos(x, y)
    if y2 < 512 and eng[y * 1024 + x] != flat[y2 * 1024 + x2]:
        bad += 1
chk('引擎像素 → flat 位置 的内容映射 (4000 个随机点)', bad == 0, '不一致 %d' % bad)
# 写入侧格位 = 引擎格位 + PHI*16 (带回绕) —— 与 ATLAS_PHI 的定义自洽
bad2 = 0
for slot in (0, 61, 62, 100, 744, 1182, 1302, 1426, 1503):
    ex, ey = tcslib.atlas_cell_xy_engine_view(slot)
    fx, fy = tcslib.atlas_cell_xy_engine(slot)
    row, col = slot // tcslib.NCOL, slot % tcslib.NCOL
    p = col + tcslib.atlas_row_phase(row)
    wx = (ex + 16 * tcslib.atlas_row_phase(row)) % 1024
    wy = ey + (1 if p >= tcslib.GRID_MOD else 0)
    if (fx, fy) != (wx, wy):
        bad2 += 1
        print('     slot=%d flat=(%d,%d) 期望(%d,%d)' % (slot, fx, fy, wx, wy))
chk('写入侧格位 = 引擎格位 + 16*PHI (带回绕)', bad2 == 0, '不一致 %d' % bad2)
chk('grid_row_alignment 行0..18 全 0',
    all(v == 0 for k, v in dump_font.grid_row_alignment().items() if k <= 18),
    str({k: v for k, v in dump_font.grid_row_alignment().items() if k >= 19}))

print('[2] GlyphCache (字库预检) 行为未变')
cs = tcslib.Charset()
iso = tcslib.Iso(zh)
try:
    g = tcslib.GlyphCache(cs, iso)
    n_ok = sum(1 for ch in cs.enc_pair if g.has_glyph(ch))
    n_rec = sum(1 for ch in cs.enc_single if g.has_glyph(ch))
    print('     pair 有字形 %d / %d; single 有字形 %d / %d'
          % (n_ok, len(cs.enc_pair), n_rec, len(cs.enc_single)))
    chk('pair 有字形 = 1319 (与改动前一致)', n_ok == 1319, '%d' % n_ok)
    chk('single 有字形 = 110', n_rec == 110, '%d' % n_rec)
finally:
    iso.close()

print('[3] EN 原版图 (新读法) 裁图')
p = os.path.join(HERE, 'dump_en', 'GR_EN_ORIG_font_atlas.png')
if os.path.isfile(p):
    im = Image.open(p)
    print('     %s mode=%s size=%s' % (os.path.basename(p), im.mode, im.size))
    im.convert('L').crop((0, 0, 768, 220)).save(os.path.join(HERE, 'c_en_newdump_topleft.png'))
    chk('EN 新图尺寸 = 1024x1024 (512x512 @2x)', im.size == (1024, 1024), str(im.size))
else:
    chk('EN 新图存在', False, p)

print('[smoke] %s' % ('全部通过 OK' if ok else '**有失败项**'))
sys.exit(0 if ok else 1)
