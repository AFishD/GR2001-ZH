# -*- coding: utf-8 -*-
r"""lead_independent_check.py — Lead 的独立读取验证 (不复用 tcslib/dump_font 的解析与格位函数)

思路:
  1) 自己按"GIF 封包流"结构重建引擎图 (每段 48B 头 + 64 行 x 512B, 段 k 放到 y=64k)
  2) 自己按 ELF 公式算每个对偶码的引擎格 (x=16*col, y=2+16*(row+3*[row>=12]))
  3) 三条硬检查:
     a) dump_font 的 charset CSV 里 cell_x/cell_y 与我的计算是否一致
     b) 每个在用字的格里是否真有墨
     c) **有没有两个字落到同一格** (映射撞车 = 读取错)
  4) 再验: 重建图与 release 里的 1x 图集 PNG 是否逐像素一致 (两条独立路径互证)
"""
import csv
import io
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'GR_ZH98.iso')

# ── 1) 取像素区原始字节 (只用 dump_font 的 TOC 定位, 解析自己做) ──
import dump_font as D  # noqa: E402

atlas = D.load_font(ISO)['atlas']
pak, px_off, W, H = atlas['pak'], atlas['px_off'], atlas['w'], atlas['h']
print('图集记录: %dx%d  psm=%#x  px_off=%#x' % (W, H, atlas.get('psm', -1), px_off))

# ── 2) 自己解析封包流 ──
blob = pak[px_off:]
STRIDE = W // 2                      # 512
ROWS = 64                            # 每段 64 行
SEGHDR = 48                          # 每段 48B 头
img = bytearray(W * H)               # 灰度: 0=墨 255=空
seg = 0
off = 0
while off + SEGHDR + STRIDE * ROWS <= len(blob):
    off += SEGHDR                    # 跳过包头
    y0 = seg * ROWS
    if y0 + ROWS > H:
        break
    for r in range(ROWS):
        row = blob[off + r * STRIDE: off + (r + 1) * STRIDE]
        base = (y0 + r) * W
        for bx, byte in enumerate(row):
            lo, hi = byte & 0xF, (byte >> 4) & 0xF
            img[base + bx * 2] = 0 if lo == 0 else 255
            img[base + bx * 2 + 1] = 0 if hi == 0 else 255
    off += STRIDE * ROWS
    seg += 1
print('自己解析出 %d 段 ⇒ 引擎图 %dx%d' % (seg, W, H))

# ── 3) 与 release 的 1x 图集互证 ──
P = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'release', 'font', 'GR_ZH98_font_atlas_1x.png')
if os.path.isfile(P):
    ref = Image.open(P).convert('L')
    rp = ref.load()
    diff = sum(1 for y in range(H) for x in range(W) if (img[y * W + x] < 128) != (rp[x, y] < 128))
    print('与 release/1x 图集逐像素比较: 差异 %d 像素 %s' % (diff, '✓ 一致' if diff == 0 else '✗ 不一致'))
else:
    print('(release 1x 图集不在, 跳过互证)')

# ── 4) 自己算格位 + 三条检查 ──
CS = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
pair_of = CS['pair_of']
LEAD_LO, LEAD_HI = 0xA1, 0xB1


def my_cell(b1, b2):
    slot = (b1 - 0xA1) * 94 + (b2 - 0xA1)
    row, col = slot // 62, slot % 62
    return 16 * col, 2 + 16 * (row + (3 if row >= 12 else 0)), slot, row, col


CSV = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'font', 'GR_ZH98_font_charset.csv')
rows = list(csv.DictReader(io.open(CSV, encoding='utf-8-sig')))
csv_cell = {}
for r in rows:
    if r.get('kind') == 'pair' and r.get('cell_x'):
        csv_cell[r['char']] = (int(r['cell_x']), int(r['cell_y']))

mismatch_cell, no_ink, collisions, checked = [], [], {}, 0
for ch, (b1, b2) in pair_of.items():
    if not (LEAD_LO <= b1 < LEAD_HI):
        continue
    checked += 1
    x, y, slot, row, col = my_cell(b1, b2)
    if ch in csv_cell and csv_cell[ch] != (x, y):
        mismatch_cell.append((ch, csv_cell[ch], (x, y)))
    ink = sum(1 for yy in range(y, y + 16) for xx in range(x, x + 16) if img[yy * W + xx] < 128)
    if ink == 0:
        no_ink.append((ch, slot, x, y))
    collisions.setdefault((x, y), []).append(ch)

dups = {k: v for k, v in collisions.items() if len(v) > 1}
print()
print('=' * 68)
print('独立验证结果 (对偶字 %d 个)' % checked)
print('=' * 68)
print('  a) CSV 格位与我的独立计算不一致 : %d 个 %s' % (len(mismatch_cell),
      ('← ' + ', '.join('%s csv=%s mine=%s' % t for t in mismatch_cell[:5])) if mismatch_cell else '✓'))
print('  b) 在用字但格里没墨(空白)      : %d 个 %s' % (len(no_ink),
      ('← ' + ', '.join('%s slot=%d' % (c, s) for c, s, _, _ in no_ink[:5])) if no_ink else '✓'))
print('  c) 两个字落到同一格(映射撞车)  : %d 处 %s' % (len(dups),
      ('← ' + '; '.join('%s=%s' % (k, ''.join(v)) for k, v in list(dups.items())[:5])) if dups else '✓'))
print()
print('  占用格数 %d / 1504 (期望 = 在用对偶字数 %d)' % (len(collisions), checked))
