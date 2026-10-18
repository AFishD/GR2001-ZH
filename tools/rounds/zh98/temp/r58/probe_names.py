# -*- coding: utf-8 -*-
r"""r58 探针6: 容器名字总览 (GR.IMG 895..915 / MENU.IMG 25..35) + 各容器 G0/G1/G2 的 >=2 连续汉字段数。
另: 普查表里出现的所有 container 名字 (含 has_cjk=yes 的)。
"""
import collections
import csv
import io
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace', line_buffering=True)
REPO = r'C:\Users\84363\Desktop\Ghost_Recon_2001_Locolization'
sys.path.insert(0, os.path.join(REPO, 'tools', 'iso_build'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
import tcslib                                                          # noqa: E402
import font_compact as FC                                              # noqa: E402

ISO107 = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'GR_ZH107.iso')
iso = tcslib.Iso(ISO107)
print('=== GR.IMG 895..915 / MENU.IMG 25..35 ===')
for tag, lba, lo, hi in (('GR.IMG', FC.GR_LBA, 895, 916), ('MENU.IMG', FC.MENU_LBA, 25, 36)):
    for idx in range(lo, hi):
        e = iso.img_entry(lba, idx)
        print('   %-9s #%-5d stored=%-9d real=%-9d %s'
              % (tag, idx, e['stored'], e['real'], e['name']))

print('\n=== 普查表: 每个 container 的行数 / has_cjk=yes 行数 / 最长汉字串 ===')
TDIR = os.path.join(REPO, 'work', 'builds', 'GR_ZH107', 'text')
agg = collections.defaultdict(lambda: dict(rows=0, cjk=0, anycjk=0, maxrun=0, cats=set(), kinds=set()))
for fn in sorted(os.listdir(TDIR)):
    if not fn.endswith('.csv') or '_view_' not in fn:
        continue
    with io.open(os.path.join(TDIR, fn), encoding='utf-8', newline='') as f:
        for r in csv.DictReader(f):
            c = (r.get('container') or '').strip().lstrip('\ufeff')
            if not c:
                continue
            a = agg[c]
            a['rows'] += 1
            a['cats'].add(r.get('category') or '?')
            a['kinds'].add(r.get('text_kind') or '?')
            try:
                run = int(r.get('cjk_run') or 0)
            except ValueError:
                run = 0
            a['maxrun'] = max(a['maxrun'], run)
            if run >= 1:
                a['anycjk'] += 1
            if (r.get('has_cjk') or '').strip() == 'yes':
                a['cjk'] += 1
withcjk = [(c, a) for c, a in agg.items() if a['anycjk']]
withcjk.sort(key=lambda kv: (-kv[1]['maxrun'], -kv[1]['anycjk'], kv[0]))
print('容器总数 %d; 有"任何汉字"行的容器 %d 个; 其中 has_cjk(=>=2连续) 的 %d 个'
      % (len(agg), len(withcjk), sum(1 for _c, a in withcjk if a['cjk'])))
print('%-46s %7s %7s %7s %7s %s' % ('container', 'rows', 'anyCJK', 'hasCJK', '最长串', 'category'))
for c, a in withcjk:
    print('%-46s %7d %7d %7d %7d %s'
          % (c, a['rows'], a['anycjk'], a['cjk'], a['maxrun'], ','.join(sorted(a['cats']))))
iso.close()
