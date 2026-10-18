# -*- coding: utf-8 -*-
"""r39 探针 13: 「长串 (>=L 全可打印) 密度」的正确测量 —— 定第 3 关。只读。"""
import collections
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
iso = T.Iso(ZH)
cs = T.Charset()
idx = FU.CharsetIndex()
conts = FU.build_container_list(iso)

# ── 用**本工具自己的扫描字母表**做长串判据 (与第 1 关同一口径) ──
ALPHA = bytes(sorted(idx.alphabet))
RUN16 = re.compile(b'[' + re.escape(ALPHA) + b']{16,}')
SCRUB = re.compile(rb'[^\x00-\xff]')


def long_ratio(blob):
    """长度 >=16 的可读串占容器字节比例 (可读串 = 本工具扫描字母表里的连续字节)"""
    tot = 0
    for m in RUN16.finditer(blob):
        g = m.group(0)
        if b'\x00' in g[:1]:
            continue
        tot += len(g)
    return tot / float(len(blob)), tot


random.seed(20261005)
print('--- 纯随机数据 16 MB ---')
rnd = bytes(random.randrange(256) for _ in range(16 << 20))
print('   长串占比 %.9f (理论命中 ~0.0 条)' % long_ratio(rnd)[0])

print('\n--- 关键容器 ---')
names = (('D01_BEACH.MIS', 'MIS'), ('DE_STRINGS.TXT', 'TXT'), ('CAMPAIGN.XML', 'XML'),
         ('DEMOLITIONS-01.ATR', 'ATR'), ('MULTIPLAYER_KIT.DIR', 'OTHER'),
         ('GR_VOXLIST.LST', 'OTHER'), ('MP04_VALLEY.BMZ', 'RSB'), ('D01_BEACH.BMZ', 'RSB'),
         ('PKM.BMZ', 'RSB'), ('MAIN_MENU_PS2.RSB', 'RSB'), ('M11_POW_CAMP.BMZ', 'RSB'),
         ('ZZZ.PSS', 'MEDIA'), ('MUSIC.TM', 'MEDIA'), ('BNK_95_05.SS', 'MEDIA'),
         ('LOGOUBI.PSS', 'MEDIA'), ('D01_BEACH.SHT', 'MEDIA'), ('D01_BEACH.AOL', 'OTHER'),
         ('SLUS_206.13', 'ELF'), ('MODULES/ILINK.IRX', 'ISO_FILE'))
by = {}
for c in conts:
    by.setdefault((c['name'], c['kind']), c)
print('%-28s %-8s %10s %12s %10s' % ('name', 'kind', 'blob', 'L>=16 占比', 'L>=16 字节'))
for (nm, kd) in names:
    c = by.get((nm, kd))
    if c is None:
        print('   !! 缺 %s' % nm)
        continue
    blob, _r = FU.container_blob(iso, c)
    r, tot = long_ratio(blob)
    print('%-28s %-8s %10d %12.6f %10d' % (nm[:28], kd, len(blob), r, tot))

print('\n--- 全盘按 kind: (long_ratio, 反引号数) 分布 ---')
agg = collections.defaultdict(list)
rows = []
for c in conts:
    blob, _r = FU.container_blob(iso, c)
    if len(blob) < 64:
        continue
    r, tot = long_ratio(blob)
    agg[c['kind']].append(r)
    rows.append(dict(kind=c['kind'], cat=None, name=c['name'], img=c['img'], idx=c['idx'],
                     blob=len(blob), lr=round(r, 8), lbytes=tot))
print('%-10s %5s %12s %12s %12s %12s' % ('kind', 'n', '中位', 'p75', 'p90', '最大'))
for k in sorted(agg):
    v = sorted(agg[k])
    p = lambda q: v[min(len(v) - 1, int(q * len(v)))]
    print('%-10s %5d %12.6f %12.6f %12.6f %12.6f' % (k, len(v), p(.5), p(.75), p(.9), v[-1]))
json.dump(rows, open(os.path.join(HERE, 'long_ratios.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)

RISKY = ('RSB', 'PAK', 'MEDIA', 'OTHER')
print('\n--- 风险类: long_ratio 阈值的效果 ---')
risky = [x for x in rows if x['kind'] in RISKY]
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
dd = dict(((x['img'], x['idx'], x['name']), x) for x in D)
for x in risky:
    y = dd.get((x['img'], x['idx'], x['name']))
    x['distinct'] = y['distinct'] if y else 0
    x['score'] = y['score'] if y else 0
    x['cjk2'] = y['cjk2'] if y else 0
    x['clean_ratio'] = y['clean_ratio'] if y else 0
for thr in (0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05):
    k = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['lr'] >= thr]
    print('   long_ratio>=%-7.4f ⇒ 容器 %4d 串 %8d cjk2 %5d 按 kind %s'
          % (thr, len(k), sum(x['distinct'] for x in k), sum(x['cjk2'] for x in k),
             dict(collections.Counter(x['kind'] for x in k))))
print('\n--- 风险类: clean_ratio>=0.002 或 long_ratio>=0.002 ---')
k = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10
     and (x['clean_ratio'] >= 0.002 or x['lr'] >= 0.002)]
print('   容器 %d 串 %d cjk2 %d 按 kind %s'
      % (len(k), sum(x['distinct'] for x in k), sum(x['cjk2'] for x in k),
         dict(collections.Counter(x['kind'] for x in k))))
print('   按 cat/名字前 18:')
for x in sorted(k, key=lambda y: -y['distinct'])[:18]:
    print('     %-8s d=%6d clean=%.5f lr=%.6f cjk2=%4d %-34s' %
          (x['kind'], x['distinct'], x['clean_ratio'], x['lr'], x['cjk2'], x['name'][:34]))
iso.close()
