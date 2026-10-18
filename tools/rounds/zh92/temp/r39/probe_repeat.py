# -*- coding: utf-8 -*-
"""r39 探针 14: 「重复率」判据 —— 真名字表里的串会重复出现, 噪声串只出现一次。只读。"""
import collections
import json
import os
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
iso = T.Iso(ZH)
cs = T.Charset()
DC._IDX = FU.CharsetIndex()
conts = FU.build_container_list(iso)

names = (('D01_BEACH.MIS', 'MIS'), ('DE_STRINGS.TXT', 'TXT'), ('CAMPAIGN.XML', 'XML'),
         ('DEMOLITIONS-01.ATR', 'ATR'), ('MULTIPLAYER_KIT.DIR', 'OTHER'),
         ('GR_VOXLIST.LST', 'OTHER'), ('MP04_VALLEY.BMZ', 'RSB'), ('D01_BEACH.BMZ', 'RSB'),
         ('PKM.BMZ', 'RSB'), ('MAIN_MENU_PS2.RSB', 'RSB'), ('M11_POW_CAMP.BMZ', 'RSB'),
         ('ZZZ.PSS', 'MEDIA'), ('MUSIC.TM', 'MEDIA'), ('BNK_95_05.SS', 'MEDIA'),
         ('BNK_99_00.SS', 'MEDIA'), ('LOGOUBI.PSS', 'MEDIA'), ('D01_BEACH.SHT', 'MEDIA'),
         ('D01_BEACH.AOL', 'OTHER'), ('SLUS_206.13', 'ELF'),
         ('MODULES/ILINK.IRX', 'ISO_FILE'), ('CHECKPOINT.SAV', 'OTHER'),
         ('NO_RESTRICTIONS.KIL', 'OTHER'), ('BNK_24.IDC', 'OTHER'))
by = {}
for c in conts:
    by.setdefault((c['name'], c['kind']), c)
print('%-26s %-8s %9s %8s %8s %9s %9s %9s' %
      ('name', 'kind', 'blob', 'distinct', 'occur', 'rep_ratio', 'exact_rep', 'longest'))
for (nm, kd) in names:
    c = by.get((nm, kd))
    if c is None:
        print('   !! 缺 %s' % nm)
        continue
    blob, _r = FU.container_blob(iso, c)
    r = DC.scan_container(blob, kd, cs, cap=200000)
    occ = sum(x['dup'] for x in r['rows'])
    dup_bytes = sum(len(x['text']) * (x['dup'] - 1) for x in r['rows'])
    tot_bytes = sum(len(x['text']) * x['dup'] for x in r['rows'])
    ex = [x for x in r['rows'] if x['exact']]
    ex_rep = (len(ex) and sum(1 for x in ex if x['dup'] > 1) / float(len(ex))) or 0.0
    longest = max((len(x['text']) for x in r['rows']), default=0)
    print('%-26s %-8s %9d %8d %8d %9.4f %9.4f %9d' %
          (nm[:26], kd, len(blob), r['distinct'], occ,
           dup_bytes / max(1.0, tot_bytes), ex_rep, longest))

print('\n--- 全盘风险类: 重复率分布 (exact 串里 dup>1 的比例) ---')
agg = collections.defaultdict(list)
rows = []
for c in conts:
    if c['kind'] not in ('RSB', 'PAK', 'MEDIA', 'OTHER'):
        continue
    blob, _r = FU.container_blob(iso, c)
    if len(blob) < 64:
        continue
    r = DC.scan_container(blob, c['kind'], cs, cap=200000)
    ex = [x for x in r['rows'] if x['exact']]
    ratio = (sum(1 for x in ex if x['dup'] > 1) / float(len(ex))) if ex else 0.0
    dup_bytes = sum(len(x['text']) * (x['dup'] - 1) for x in r['rows'])
    tot_bytes = sum(len(x['text']) * x['dup'] for x in r['rows'])
    bratio = dup_bytes / max(1.0, tot_bytes)
    rows.append(dict(kind=c['kind'], name=c['name'], img=c['img'], idx=c['idx'],
                     blob=len(blob), distinct=r['distinct'], exact=len(ex),
                     clean=r['clean'], rep=round(ratio, 4), brep=round(bratio, 4)))
    agg[c['kind']].append(ratio)
json.dump(rows, open(os.path.join(HERE, 'repeat_ratios.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
print('%-10s %5s %10s %10s %10s %10s' % ('kind', 'n', '中位', 'p75', 'p90', '最大'))
for k in sorted(agg):
    v = sorted(agg[k])
    p = lambda q: v[min(len(v) - 1, int(q * len(v)))]
    print('%-10s %5d %10.4f %10.4f %10.4f %10.4f' % (k, len(v), p(.5), p(.75), p(.9), v[-1]))
print('\n--- 参考: 非风险类的中位重复率 ---')
for k in ('MIS', 'ATR', 'XML', 'RES', 'TXT', 'ELF', 'ISO_FILE'):
    v = []
    for c in conts:
        if c['kind'] != k:
            continue
        blob, _r = FU.container_blob(iso, c)
        if len(blob) < 64:
            continue
        r = DC.scan_container(blob, k, cs, cap=200000)
        ex = [x for x in r['rows'] if x['exact']]
        v.append((sum(1 for x in ex if x['dup'] > 1) / float(len(ex))) if ex else 0.0)
    v.sort()
    if v:
        print('   %-9s n=%4d 中位 %.4f  p25 %.4f' % (k, len(v), v[len(v) // 2], v[len(v) // 4]))
iso.close()
