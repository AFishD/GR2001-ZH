# -*- coding: utf-8 -*-
r"""zero_probe.py — 三个决定性探针（只读）
 [1] 364 个缺字用现役配方 (gen_font16::render16) 逐字试渲 ⇒ ok / overflow / ttf_missing / 空
 [2] 三个 face 的记录表: 哪些 y 带是"活的"(被记录引用) ⇒ y450..498 / y480..495 能不能回收
 [3] 单字节码 0xB1..0xB4 是什么字、在当前文本里出现多少次（决定抬 gate 的代价）
"""
import csv
import json
import os
import re
import struct
import sys
from collections import Counter, defaultdict

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import tcslib  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r81')
os.makedirs(OUT, exist_ok=True)
LS = []


def say(s=''):
    print(s)
    LS.append(s)


CHARSET = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
cs = json.load(open(CHARSET, encoding='utf-8'))
codes = {k: int(v) for k, v in cs['codes'].items()}
pair_of = {k: tuple(v) for k, v in cs['pair_of'].items()}
AVAIL = set(codes) | set(pair_of)

# 缺字清单（A1 产物）
mc = os.path.join(OUT, 'missing_chars.csv')
missing = []
with open(mc, encoding='utf-8-sig', newline='') as f:
    for row in csv.DictReader(f):
        missing.append(row)
say('[1] 缺字清单 %d 种' % len(missing))

# ---- [1] 渲染探针 ----
FZ16 = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
fnt = ImageFont.truetype(FZ16, 16)


def render16(ch):
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    win = a[8:24, 8:24]
    out = win < 128
    full = a < 128
    res = dict(ink=int(out.sum()), empty=not bool(out.any()))
    if out.any():
        fys, fxs = np.where(full)
        res['overflow'] = bool(fys.min() < 8 or fxs.min() < 8 or fys.max() >= 24 or fxs.max() >= 24)
        res['bbox'] = [int(fxs.min()) - 8, int(fys.min()) - 8, int(fxs.max()) - 8, int(fys.max()) - 8]
    else:
        res['overflow'] = False
    return out, res


stat = Counter()
probe = []
for row in missing:
    ch = row['char']
    g, r = render16(ch)
    cls = 'ttf_missing' if r['empty'] else ('overflow' if r['overflow'] else 'ok')
    stat[cls] += 1
    probe.append(dict(char=ch, codepoint=row['codepoint'], count=int(row['count']),
                      in_entries=int(row['in_entries']), cls=cls, ink=r['ink'],
                      bbox=r.get('bbox')))
    if cls == 'ok':
        ys, xs = np.where(g)
        # 检查墨是否贴边（0 或 15）
        if ys.min() == 0 or xs.min() == 0 or ys.max() == 15 or xs.max() == 15:
            stat['ok_edges'] += 1
say('    渲染判定: %s' % dict(stat))
say('    可渲染 (ok) = %d / %d' % (stat['ok'], len(missing)))
json.dump(probe, open(os.path.join(OUT, 'render_probe_364.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

# ---- [2] 记录表活带 ----
ISO = os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'GR_ZH113b.iso')
iso = tcslib.Iso(ISO)
MENU_LBA = 776286
base = MENU_LBA * 2048
e4 = iso.img_entry(MENU_LBA, 4)
slot = iso.read(base + e4['off'], e4['stored'])
sys.path.insert(0, os.path.join(REPO, 'tools', 'hanliu', 'tools'))
from lz77_decode import decode_entry  # noqa: E402
ft, _ = decode_entry(slot)
p, faces = tcslib.parse_ft_faces(ft)
say('')
say('[2] FONT.RES 解出 %d B ; styles 起点 0x%X' % (len(ft), p))
for nm, fld, recs in faces:
    vs = Counter()
    for r in recs:
        vs[(r[3], r[5])] += 1
    say('  face %-8r nrec=%d ; (v0,v1) 组合 %d 种' % (nm, fld[4] * fld[5], len(vs)))
    for (v0, v1), c in sorted(vs.items()):
        mark = ''
        if v0 >= 440:
            mark = '   ← y>=440 带'
        say('      v0=%-4d v1=%-4d 记录 %d 条%s' % (v0, v1, c, mark))

# ---- [3] 单字节 0xB1..0xB4 用量 ----
say('')
say('[3] 单字节码 0xB1..0xB4 与当前文本用量')
code2ch = {v: k for k, v in codes.items()}
for b in (0xB1, 0xB2, 0xB3, 0xB4, 0xB5):
    say('    0x%02X -> %r  bar_x_used_by = %d 处  (pair lead? %s)'
        % (b, code2ch.get(b), 0, 'yes' if b in {0xA1 + i for i in range(16)} else 'no'))
# 统计当前盘文本里这些字节
for tag, d in (('GR_ZH113b/text', os.path.join(REPO, 'work', 'builds', 'GR_ZH113b', 'text')),):
    import glob as _g
    cnt = Counter()
    rows = 0
    for fp in sorted(_g.glob(os.path.join(d, '*_text_*.csv'))):
        if '_view_' in os.path.basename(fp):
            continue
        with open(fp, encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                t = row.get('text_edited') or ''
                if not t:
                    continue
                rows += 1
                for b in (0xB1, 0xB2, 0xB3, 0xB4):
                    ch = code2ch.get(b)
                    if ch:
                        cnt[b] += t.count(ch)
                cnt['all_b1_icon'] += t.count('\ue0b1')
    say('    %s: 已改行 %d' % (tag, rows))
    for k in sorted(cnt, key=str):
        say('      %-12s %d' % (k, cnt[k]))

iso.close()
open(os.path.join(OUT, 'probe.txt'), 'w', encoding='utf-8').write('\n'.join(LS) + '\n')
print('\n[OUT] %s' % os.path.join(OUT, 'probe.txt'))
