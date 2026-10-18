# -*- coding: utf-8 -*-
"""r39 探针 10: 「可读字节占比」能否干净地区分「贴图名表」与「压缩噪声」。只读。"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'text_csv'))
sys.path.insert(0, os.path.join(REPO, 'tools', 'font_pipeline'))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import tcslib as T
import font_usage as FU
import dump_containers as DC

ZH = os.path.join(REPO, 'work', 'builds', 'GR_ZH92', 'GR_ZH92.iso')
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
risky = [x for x in D if x['risk']]

iso = T.Iso(ZH)
cs = T.Charset()
DC._IDX = FU.CharsetIndex()
conts = FU.build_container_list(iso)
by = dict(((c['img'], c['idx'], c['name']), c) for c in conts)

names = (('MP04_VALLEY.BMZ', 'RSB'), ('D01_BEACH.BMZ', 'RSB'), ('PKM.BMZ', 'RSB'),
         ('MAIN_MENU_PS2.RSB', 'RSB'), ('M11_POW_CAMP.BMZ', 'RSB'),
         ('ZZZ.PSS', 'MEDIA'), ('MUSIC.TM', 'MEDIA'), ('BNK_95_03.SS', 'MEDIA'),
         ('D01_BEACH.SHT', 'MEDIA'), ('D01_BEACH.AOL', 'OTHER'),
         ('CHECKPOINT.SAV', 'OTHER'), ('NO_RESTRICTIONS.KIL', 'OTHER'),
         ('D01_BEACH.MIS', 'MIS'), ('EN_STRINGS.RES', 'RES'),
         ('DE_STRINGS.TXT', 'TXT'), ('CAMPAIGN.XML', 'XML'),
         ('DEMOLITIONS-01.ATR', 'ATR'), ('SLUS_206.13', 'ELF'), ('SYSTEM.CNF', 'ISO_FILE'))
print('%-28s %-8s %10s %8s %8s %8s %8s %8s' %
      ('name', 'kind', 'blob', 'distinct', 'score', 'msgR', 'tokQ%', 'cleanB%'))
for (nm, kd) in names:
    hit = [c for c in conts if c['name'] == nm and c['kind'] == kd]
    if not hit:
        print('   !! 找不到 %s (%s)' % (nm, kd))
        continue
    c = hit[0]
    blob, _r = FU.container_blob(iso, c)
    r = DC.scan_container(blob, kd, cs)
    clean_b = junk_b = 0
    for x in r['rows']:
        nb = len(x['text'].encode('utf-8'))
        if x['exact'] and not re.search(r'[\ue000-\uf8ff]', x['text']):
            clean_b += nb
        else:
            junk_b += nb
    mb = max(1.0, len(blob) / 1048576.0)
    tokq = (clean_b + junk_b) and clean_b / float(clean_b + junk_b) or 0.0
    print('%-28s %-8s %10d %8d %8.2f %8.3f %8.3f %8.4f' %
          (nm[:28], kd, len(blob), r['distinct'], r['distinct'] / mb,
           (r['msg'] / max(1, r['distinct'])), tokq, clean_b / float(len(blob))))

print('\n--- 全 risky 容器: clean_byte_ratio 分布 (抽样扫描) ---')
rows = []
for x in risky:
    hit = by.get((x['img'], x['idx'], x['name']))
    if hit is None:
        continue
    blob, _r = FU.container_blob(iso, hit)
    if not blob:
        continue
    r = DC.scan_container(blob, x['kind'], cs)
    clean_b = 0
    for t in r['rows']:
        if t['exact']:
            clean_b += len(t['text'])
    rows.append(dict(name=x['name'], kind=x['kind'], blob=len(blob), d=r['distinct'],
                     msgR=x['msg_ratio'], score=x['score'],
                     clean=clean_b / float(len(blob)), tokQ=clean_b / max(1.0, float(x['blob']))))
json.dump(rows, open(os.path.join(HERE, 'clean_ratios.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
for thr in (0.002, 0.005, 0.01, 0.02, 0.05, 0.10):
    keep = [r for r in rows if r['clean'] >= thr]
    nb = sum(r['d'] for r in keep)
    print('   clean 占比 >= %-6.3f ⇒ 容器 %4d, 串 %7d' % (thr, len(keep), nb))
print('\n--- clean 占比最高的 20 个 ---')
for r in sorted(rows, key=lambda y: -y['clean'])[:20]:
    print('   clean=%.4f d=%6d msgR=%.3f score=%8.2f %-9s %s' %
          (r['clean'], r['d'], r['msgR'], r['score'], r['kind'], r['name'][:40]))
print('\n--- clean 占比 < 0.002 但有 cjk2 的容器数 ---')
print('   %d' % len([r for r in rows if r['clean'] < 0.002]))
iso.close()
