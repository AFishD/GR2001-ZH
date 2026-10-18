# -*- coding: utf-8 -*-
"""r39: 最终闸门下 binary_assets 的成分分析; 选 --max-rows-per-category 的截断口径。只读。"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
risky = [x for x in D if x['risk']]
keep = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['clean_ratio'] >= 0.002]
print('放行 %d 容器 串 %d' % (len(keep), sum(x['distinct'] for x in keep)))
print('按 kind: %s' % dict(collections.Counter(x['kind'] for x in keep)))
print('按 kind 的串数: %s' % dict(
    (k, sum(x['distinct'] for x in keep if x['kind'] == k))
    for k in sorted(set(x['kind'] for x in keep))))

print('\n--- 按 clean_ratio 降序 (前 30) ---')
for x in sorted(keep, key=lambda y: -y['clean_ratio'])[:30]:
    print('   clean=%.5f d=%6d score=%9.2f tr=%.3f %-9s %-34s %10d B' %
          (x['clean_ratio'], x['distinct'], x['score'], x['text_ratio'], x['kind'],
           x['name'][:34], x['blob']))

print('\n--- 若按 clean_ratio 降序累计到 20000 行, 会取多少个容器/哪些 kind ---')
tot = 0
sel = []
for x in sorted(keep, key=lambda y: -y['clean_ratio']):
    if tot >= 20000:
        break
    sel.append(x)
    tot += x['distinct']
print('   容器 %d 个, 串 %d; 按 kind %s' % (len(sel), tot,
                                     dict(collections.Counter(y['kind'] for y in sel))))
print('   落在最后 (clean_ratio 最低) 的 5 个:')
for x in sel[-5:]:
    print('      clean=%.5f d=%5d %-9s %s' % (x['clean_ratio'], x['distinct'], x['kind'], x['name'][:38]))

print('\n--- 各 clean_ratio 区间的容器数 / 串数 ---')
bins = [(0.002, 0.005), (0.005, 0.01), (0.01, 0.05), (0.05, 0.2), (0.2, 1.01)]
for (a, b) in bins:
    v = [x for x in keep if a <= x['clean_ratio'] < b]
    print('   [%.3f, %.3f): 容器 %4d 串 %7d  按 kind %s' %
          (a, b, len(v), sum(x['distinct'] for x in v),
           dict(collections.Counter(x['kind'] for x in v))))
print('\n--- MEDIA 里放行的容器 (clean_ratio>=0.002) ---')
mv = [x for x in keep if x['kind'] == 'MEDIA']
print('   %d 个, 串 %d' % (len(mv), sum(x['distinct'] for x in mv)))
for x in sorted(mv, key=lambda y: -y['clean_ratio'])[:14]:
    print('      clean=%.5f d=%5d %-34s' % (x['clean_ratio'], x['distinct'], x['name'][:34]))
