# -*- coding: utf-8 -*-
r"""r2_select.py — round67 第 2 步: 从 missing_chars.csv 选 329 个字, 并逐字做**可渲染性**检验。

选字依据 (报告里要写清):
  1. 只从 `work/builds/GR_ZH98/temp/r64/missing_chars.csv` 里选 (那份 = 用户**丰富版**文本
     "字库没有的字" 的 693 种字, 按出现次数降序; 由 r64_missing.py 产出)。
  2. 排序 = 出现次数降序; 同频按码位升序 (保证**可复跑、结果稳定**)。
  3. 逐个用 `方正像素16.ttf` 按 `gen_font16.render16` **同一配方**渲染, 三类拒收:
       · `ttf_missing`  — 16px em 窗里一个墨点都没有 (TTF 没这个字形)
       · `overflow`     — 墨越出 16x16 em 窗 (画出来会被裁, 观感损坏)
       · `zombie`       — `<128` 阈值渲染为空 (同 ttf_missing 的另一种表现)
  4. 取**前 329 个通过检验**的, 顺序填进 slot 1175..1503 (高频 → 低 slot)。
     拒收的字**跳过并顺延**给后面的候选 (693 >> 329, 余量充足)。

本脚本**只读**, 产出:
  · `r2_render_probe.json` — 693 个候选逐字的渲染判定 (含墨量/包围盒)
  · `r2_selection.csv`     — 入选 329 条 (char, codepoint, count, in_entries, slot, lead, trail, ink)
"""
import csv
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib                                                             # noqa: E402

MISS = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r64', 'missing_chars.csv')
TTF = os.path.join(REPO, 'third_party', 'fonts', '方正像素16.ttf')
WANT = 329
SLOT_LO = 1175                       # = tcslib.pair_slot(0xAD, 0xD0)
assert tcslib.pair_slot(0xAD, 0xD0) == SLOT_LO

from PIL import Image, ImageDraw, ImageFont                              # noqa: E402

print('[font] %s  exists=%s' % (TTF, os.path.isfile(TTF)))
fnt = ImageFont.truetype(TTF, 16)


def render16(ch):
    """与 gen_font16.render16 / single_cell_font.Templates.get **逐字同款**。

    返回 (bitmap(16x16 bool), verdict, bbox)。bbox = 全程 32x32 canvas 上墨的包围盒。
    """
    img = Image.new('L', (32, 32), 255)
    ImageDraw.Draw(img).text((8, 8), ch, font=fnt, fill=0)
    a = np.asarray(img)
    win = a[8:24, 8:24] < 128
    full = a < 128
    if not full.any():
        return win, 'ttf_missing', None
    ys, xs = np.where(full)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    if not win.any():
        return win, 'zombie', bbox
    if ys.min() < 8 or xs.min() < 8 or ys.max() >= 24 or xs.max() >= 24:
        return win, 'overflow', bbox
    return win, 'ok', bbox


# ---------- 读候选 ----------
rows = list(csv.DictReader(io.open(MISS, encoding='utf-8-sig', newline='')))
print('[in] %s : %d 行' % (os.path.basename(MISS), len(rows)))
cand = []
for r in rows:
    ch = r['char']
    cand.append(dict(ch=ch, cp=r['codepoint'], count=int(r['count']),
                     in_entries=int(r['in_entries']), sample=r['sample_entries']))
# 稳定排序: 次数降序, 同频按码位升序
cand.sort(key=lambda d: (-d['count'], int(d['cp'][2:], 16)))
assert len(cand) == 693, len(cand)
assert len({c['ch'] for c in cand}) == 693

cs = json.load(io.open(os.path.join(REPO, 'tools', 'font_pipeline', 'data',
                                    'charset_compiled_zh16.json'), encoding='utf-8'))
have = set(cs['pair_of']) | set(cs['codes'])
dup = [c['ch'] for c in cand if c['ch'] in have]
print('[in] 候选里已在现役 charset 的 = %d %s' % (len(dup), dup[:10]))
assert not dup, dup

# ---------- 逐字渲染检验 ----------
probe, ok_list, bad = [], [], []
for c in cand:
    bm, verdict, bbox = render16(c['ch'])
    ink = int(bm.sum())
    rec = dict(ch=c['ch'], cp=c['cp'], count=c['count'], verdict=verdict,
               ink=ink, bbox=bbox)
    probe.append(rec)
    c['ink'] = ink
    c['verdict'] = verdict
    (ok_list if verdict == 'ok' else bad).append(c)

from collections import Counter                                                  # noqa: E402
vc = Counter(r['verdict'] for r in probe)
print('[render] 693 个候选判定: %s' % dict(vc))
for c in bad:
    print('   拒收 %s %s  %s  count=%d' % (c['ch'], c['cp'], c['verdict'], c['count']))
print('[render] 可渲染 %d 个 ⇒ 需要 %d, %s'
      % (len(ok_list), WANT, '充足' if len(ok_list) >= WANT else '★不足!'))
assert len(ok_list) >= WANT, '可渲染字不足 %d' % WANT

sel = ok_list[:WANT]
# ---------- 分配格位 ----------
for i, c in enumerate(sel):
    slot = SLOT_LO + i
    b1, b2 = tcslib.pair_from_slot(slot)
    c['slot'] = slot
    c['lead'] = b1
    c['trail'] = b2
    c['cell'] = list(tcslib.atlas_cell_xy_engine_view(slot))

# 硬断言: 329 个 slot 恰为 1175..1503, lead≤0xB0, trail 0xA1..0xFE
slots = [c['slot'] for c in sel]
assert slots == list(range(SLOT_LO, SLOT_LO + WANT))
assert max(c['lead'] for c in sel) == 0xB0, hex(max(c['lead'] for c in sel))
assert min(c['lead'] for c in sel) == 0xAD
assert all(0xA1 <= c['trail'] <= 0xFE for c in sel)
lead_hist = Counter(c['lead'] for c in sel)
print('[slot] 分配 %d 格: %s' % (len(sel), {hex(k): v for k, v in sorted(lead_hist.items())}))
print('[slot] slot %d..%d; 单元格 (x,y) 右缘 max=%d 底缘 max=%d'
      % (slots[0], slots[-1],
         max(c['cell'][0] for c in sel) + 16, max(c['cell'][1] for c in sel) + 16))
print('[pick] 入选字数 %d; 最低入选频次 %d; 被跳过(不可渲染) %d; 落选(名额用尽) %d'
      % (len(sel), sel[-1]['count'], len(bad), len(ok_list) - WANT))
print('[pick] 前 12 个: %s' % ' '.join('%s(%d)' % (c['ch'], c['count']) for c in sel[:12]))
print('[pick] 后 5 个:  %s' % ' '.join('%s(%d)' % (c['ch'], c['count']) for c in sel[-5:]))

# 覆盖率: 入选字覆盖了 rich 文本里多少"缺字出现次数"
tot_occ = sum(c['count'] for c in cand)
sel_occ = sum(c['count'] for c in sel)
print('[cover] 入选 %d/%d 种字, 覆盖缺字出现次数 %d/%d = %.1f%%'
      % (len(sel), len(cand), sel_occ, tot_occ, 100.0 * sel_occ / tot_occ))

json.dump(dict(probe=probe, verdicts=dict(vc), n_ok=len(ok_list), n_bad=len(bad),
               bad=[dict(ch=c['ch'], cp=c['cp'], verdict=c['verdict'], count=c['count'])
                    for c in bad],
               selected=[dict(ch=c['ch'], cp=c['cp'], count=c['count'],
                              in_entries=c['in_entries'], slot=c['slot'],
                              lead=c['lead'], trail=c['trail'], ink=c['ink'],
                              cell=c['cell']) for c in sel]),
          io.open(os.path.join(HERE, 'r2_render_probe.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)

CANON = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_expand_zh113.csv')
for path in (os.path.join(HERE, 'r2_selection.csv'), CANON):
    with io.open(path, 'w', encoding='utf-8', newline='\n') as fh:
        w = csv.writer(fh)
        w.writerow(['char', 'codepoint', 'count', 'in_entries', 'slot', 'new_lead',
                    'new_trail', 'cell_x', 'cell_y', 'ink'])
        for c in sel:
            w.writerow([c['ch'], c['cp'], c['count'], c['in_entries'], c['slot'],
                        '0x%02X' % c['lead'], '0x%02X' % c['trail'],
                        c['cell'][0], c['cell'][1], c['ink']])
    print('[OUT] %s' % path)
print('[OUT] r2_render_probe.json')
