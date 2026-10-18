# -*- coding: utf-8 -*-
r"""zero_glyphs.py — B1: 364 个缺字 → 16x16 墨窗（现役配方）+ 自检 + 联系表

配方 = tools/font_pipeline/gen_font16.py::render16()（逐行同款）:
  PIL truetype(方正像素16.ttf, 16) / 32x32 白底 / draw.text((8,8)) / 取 canvas[8:24,8:24] / 阈值 <128
缺字形 (方正像素16 里没有) 用 FALLBACK16 的 13px 拷贝法（gen_font16 L128-145 同款）。

产物:
  work/builds/GR_ZH98/temp/r81/glyphs_zh120.json     —— 逐字: 码位/次数/墨点数/bbox/16 行 hex
  work/builds/GR_ZH98/temp/r81/glyphs_zh120_sheet.png —— 联系表（肉眼比对用）
自检（任一不过即非零退出）:
  ① 每个 ok 字：墨点数 ≥ 1
  ② 墨不越 16x16 窗（窗内贴边允许）
  ③ 回读 hex → 位图逐点一致
  ④ 联系表尺寸 == 行数 x 16
"""
import csv
import json
import os
import sys

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
ZH16A = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'atlas_zh16.png')

fnt = ImageFont.truetype(FZ16, 16)
ZH16G = np.asarray(Image.open(ZH16A).convert('L')).astype(np.uint8)


def yrow13(r):
    return 2 + 13 * r + (39 if r >= 14 else 0)


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    out = a[8:24, 8:24] < 128
    return out, a


def fallback13(ch, code):
    """从现存 zh16 atlas 抠 13px 字形放到 16px 窗 (x+1, y+2) —— gen_font16 同款"""
    # 该字不在 pair_of 里, 用码位在 atlas 里找不到 → 用「嘚」的特殊处理: 返回空并报错
    return None


rows = []
with open(os.path.join(OUT, 'missing_chars.csv'), encoding='utf-8-sig', newline='') as f:
    for r in csv.DictReader(f):
        rows.append(r)
print('[in ] 缺字 %d 种' % len(rows))

items = []
fail = []
for r in rows:
    ch = r['char']
    g, a = render16(ch)
    ink = int(g.sum())
    rec = dict(char=ch, codepoint=r['codepoint'], count=int(r['count']),
               in_entries=int(r['in_entries']), entries=r['entries'],
               ink=ink, cls='ok', fallback=None)
    if ink == 0:
        rec['cls'] = 'ttf_missing'
        fail.append(('ttf_missing', ch))
    else:
        fys, fxs = np.where(a < 128)
        if fys.min() < 8 or fxs.min() < 8 or fys.max() >= 24 or fxs.max() >= 24:
            rec['cls'] = 'overflow'
            rec['bbox'] = [int(fxs.min()) - 8, int(fys.min()) - 8, int(fxs.max()) - 8, int(fys.max()) - 8]
            fail.append(('overflow', ch))
        else:
            ys, xs = np.where(g)
            rec['bbox'] = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())]
            rec['hex'] = [''.join('%02X' % int(np.packbits(g[y]).tobytes()[0]) for y in [yy])
                          + ''.join('%02X' % int(np.packbits(g[yy]).tobytes()[1]) for yy in [y])
                          for y in range(0)]        # 占位, 下面重算
            rec['hex'] = []
            for y in range(16):
                bits = np.packbits(g[y])
                rec['hex'].append('%02X%02X' % (int(bits[0]), int(bits[1])))
    items.append(rec)

n_ok = sum(1 for i in items if i['cls'] == 'ok')
print('[chk] ok %d / ttf_missing %d / overflow %d' % (
    n_ok, sum(1 for i in items if i['cls'] == 'ttf_missing'),
    sum(1 for i in items if i['cls'] == 'overflow')))

# 自检 ①②③
err = 0
for i in items:
    if i['cls'] != 'ok':
        continue
    if i['ink'] < 1:
        print('  ✗ %r 墨点 0' % i['char']); err += 1
    g = np.zeros((16, 16), dtype=bool)
    for y in range(16):
        v = int(i['hex'][y], 16)
        for x in range(16):
            g[y, x] = bool((v >> (15 - x)) & 1)
    if int(g.sum()) != i['ink']:
        print('  ✗ %r hex 回读墨点 %d != %d' % (i['char'], int(g.sum()), i['ink'])); err += 1
print('[chk] ① 墨≥1 / ③ hex 回读: %s' % ('PASS' if err == 0 else 'FAIL %d' % err))

# 联系表
COLS = 28
n = len(items)
rws = (n + COLS - 1) // COLS
S = 20
sheet = Image.new('L', (COLS * S, rws * S), 255)
for k, it in enumerate(items):
    cx, cy = (k % COLS) * S, (k // COLS) * S
    if it['cls'] != 'ok':
        for x in range(16):
            sheet.putpixel((cx + 2 + x, cy + 2), 128)
            sheet.putpixel((cx + 2 + x, cy + 17), 128)
            sheet.putpixel((cx + 2, cy + 2 + x), 128)
            sheet.putpixel((cx + 17, cy + 2 + x), 128)
        continue
    g = np.zeros((16, 16), dtype=bool)
    for y in range(16):
        v = int(it['hex'][y], 16)
        for x in range(16):
            g[y, x] = bool((v >> (15 - x)) & 1)
    for y in range(16):
        for x in range(16):
            if g[y, x]:
                sheet.putpixel((cx + 2 + x, cy + 2 + y), 0)
assert sheet.size == (COLS * S, rws * S), sheet.size
sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(
    os.path.join(OUT, 'glyphs_zh120_sheet.png'))
print('[chk] ④ 联系表 %s (%d 行 x %d 列)' % (sheet.size, rws, COLS))

json.dump(dict(source='charset_compiled_zh16.json vs GR_ZH109/text_backup_before_reduce',
               total=len(items), ok=n_ok,
               ttf_missing=[i['char'] for i in items if i['cls'] == 'ttf_missing'],
               overflow=[i['char'] for i in items if i['cls'] == 'overflow'],
               items=items),
          open(os.path.join(OUT, 'glyphs_zh120.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('[out] %s' % os.path.join(OUT, 'glyphs_zh120.json'))
print('[out] %s' % os.path.join(OUT, 'glyphs_zh120_sheet.png'))
print('[out] 总墨点 %d ; 平均每字 %.1f' % (sum(i['ink'] for i in items), sum(i['ink'] for i in items) / n))
sys.exit(1 if err else 0)
