# -*- coding: utf-8 -*-
r"""r71_recon.py — 混合路线第二轮的侦察

目标: 用户新译文相对**新字库(1504)**还差哪些字, 它们出现在哪些条目,
      能否把改动**限制在低精准度场景**(开发手记 / 专家介绍)?
输入: 用户的丰富版文本 = work/builds/GR_ZH109/text_backup_before_wrapfix/GR_ZH109_text_long.csv
      (text_edited 列 = 用户新译; 已修过 {Warp}{Warp})
输出: work/builds/GR_ZH98/temp/r71/ 下的清单
"""
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
RICH = os.path.join(REPO, 'work', 'builds', 'GR_ZH109', 'text_backup_before_wrapfix')
CS = os.path.join(REPO, 'tools', 'font_pipeline', 'data', 'charset_compiled_zh16.json')
OUT = os.path.join(REPO, 'work', 'builds', 'GR_ZH98', 'temp', 'r71')
os.makedirs(OUT, exist_ok=True)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

c = json.load(io.open(CS, encoding='utf-8'))
have = set(c['pair_of']) | set(c['codes'])
print('新字库: pair %d + single %d = %d 字' % (len(c['pair_of']), len(c['codes']), len(have)))

# 场景分类: 按条目 id 判断
DEV = {'SFXML:T0067', 'SFXML:T0068', 'SFXML:T0069'}          # 开发手记 1/2/3
# 专家介绍 = 人物档案页 (T0050~T0062 区间, 用标题行特征再确认)
def scene(eid, text):
    if eid in DEV:
        return '开发手记'
    if re.match(r'SFXML:T00(5[0-9]|6[0-2])$', eid):
        return '专家介绍'
    if eid.startswith('SFXML:T00'):
        return '特别收录其它'
    return '其它(语言表/菜单等)'

miss = Counter()
rows_out = []
scene_miss = Counter()
scene_occ = Counter()
for fn in sorted(os.listdir(RICH)):
    if not re.search(r'_text_[^/\\]*\.csv$', fn):
        continue
    rows = list(csv.DictReader(io.open(os.path.join(RICH, fn), encoding='utf-8-sig', newline='')))
    for r in rows:
        t = (r.get('text_edited') or '').strip()
        if not t:
            continue
        t2 = re.sub(r'\{[Ww][Aa][Rr][Pp]\}', '', t)
        want = [ch for ch in t2 if ord(ch) >= 0x80 and ch not in have]
        if not want:
            continue
        sc = scene(r['id'], t2)
        u = sorted(set(want))
        scene_miss[sc] += len(u)
        scene_occ[sc] += len(want)
        miss.update(want)
        rows_out.append(dict(table=fn, id=r['id'], scene=sc, n_kinds=len(u),
                             n_occ=len(want), missing=''.join(u), head=t2[:46].replace('\n', ' ')))

print()
print('=== 还缺字的总账 ===')
print('  不同字 %d 种 ; 共出现 %d 次 ; 涉及条目 %d 个' % (len(miss), sum(miss.values()), len(rows_out)))
print()
print('=== 按场景 ===')
for sc, n in scene_miss.most_common():
    print('  %-14s 缺 %3d 种 / %4d 次   (条目 %d 个)' %
          (sc, n, scene_occ[sc], sum(1 for r in rows_out if r['scene'] == sc)))
low = scene_miss['开发手记'] + scene_miss['专家介绍']
lowocc = scene_occ['开发手记'] + scene_occ['专家介绍']
print()
print('  ★ 低精准度场景(开发手记+专家介绍) 覆盖: %d/%d 种 (%.1f%%) ; %d/%d 次 (%.1f%%)'
      % (low, len(miss), 100.0 * low / max(1, len(miss)), lowocc, sum(miss.values()),
         100.0 * lowocc / max(1, sum(miss.values()))))
print('  ⇒ 剩下的 %d 种必须在**高精准度场景**里改' % (len(miss) - low))

with io.open(os.path.join(OUT, 'r71_entries.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['table', 'id', 'scene', 'n_kinds', 'n_occ', 'missing', 'head'])
    for r in sorted(rows_out, key=lambda x: (-x['n_occ'], x['id'])):
        w.writerow([r[k] for k in ('table', 'id', 'scene', 'n_kinds', 'n_occ', 'missing', 'head')])

with io.open(os.path.join(OUT, 'r71_chars.csv'), 'w', encoding='utf-8-sig', newline='') as f:
    w = csv.writer(f)
    w.writerow(['char', 'codepoint', 'count', 'scenes'])
    ch_scene = defaultdict(set)
    for r in rows_out:
        for ch in r['missing']:
            ch_scene[ch].add(r['scene'])
    for ch, n in miss.most_common():
        w.writerow([ch, 'U+%04X' % ord(ch), n, ' '.join(sorted(ch_scene[ch]))])
print()
print('→ %s' % os.path.join(OUT, 'r71_entries.csv'))
print('→ %s' % os.path.join(OUT, 'r71_chars.csv'))
print()
print('=== 高精准度场景里还缺哪些字 (必须处理的部分) ===')
hi = [(ch, n) for ch, n in miss.most_common()
      if '开发手记' not in ch_scene[ch] and '专家介绍' not in ch_scene[ch]]
print('  %d 种:' % len(hi), ' '.join('%s%d' % (ch, n) for ch, n in hi[:40]))
