# -*- coding: utf-8 -*-
"""r39: 新 debug 字段分析 —— 到底哪些容器被放行、为什么 25 万行。只读。"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
risky = [x for x in D if x['risk']]
print('risky=%d ; 字段=%s' % (len(risky), sorted(risky[0].keys())))

keep = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10
        and (x['clean_ratio'] >= 0.002 or x['text_ratio'] >= 0.15)]
print('放行 %d 容器, 串 %d' % (len(keep), sum(x['distinct'] for x in keep)))
print('  按 kind: %s' % dict(collections.Counter(x['kind'] for x in keep)))
print('  按 cat : %s' % dict(collections.Counter(x['cat'] for x in keep)))
print('  达上限(2000)的容器: %d' % sum(1 for x in keep if x['capped']))
print('  未达上限的串数合计: %d' % sum(x['distinct'] for x in keep if not x['capped']))

print('\n--- 放行容器按串数 top 20 ---')
for x in sorted(keep, key=lambda y: -y['distinct'])[:20]:
    print('   %-8s d=%6d clean=%.6f tr=%.3f score=%9.2f capped=%d %-34s %10d B' %
          (x['kind'], x['distinct'], x['clean_ratio'], x['text_ratio'], x['score'],
           x['capped'], x['name'][:34], x['blob']))

print('\n--- 若加「clean_ratio>=0.002 或 text_ratio>=0.30」 ---')
for m in (0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.70):
    k2 = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10
          and (x['clean_ratio'] >= 0.002 or x['text_ratio'] >= m)]
    print('   text_ratio>=%.2f ⇒ 容器 %4d 串 %7d (capped %d)'
          % (m, len(k2), sum(x['distinct'] for x in k2), sum(1 for x in k2 if x['capped'])))

print('\n--- 只靠 clean_ratio>=0.002 放行的 (不看 text_ratio) ---')
k3 = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['clean_ratio'] >= 0.002]
print('   容器 %d 串 %d; 达上限 %d; 按 kind %s'
      % (len(k3), sum(x['distinct'] for x in k3), sum(1 for x in k3 if x['capped']),
         dict(collections.Counter(x['kind'] for x in k3))))
print('\n--- 只靠 text_ratio>=0.15 放行的 ---')
k4 = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['text_ratio'] >= 0.15]
print('   容器 %d 串 %d; 达上限 %d; 按 kind %s'
      % (len(k4), sum(x['distinct'] for x in k4), sum(1 for x in k4 if x['capped']),
         dict(collections.Counter(x['kind'] for x in k4))))
print('   它们里 cjk2 合计 %d' % sum(x['cjk2'] for x in k4))
print('\n--- text_ratio>=0.15 放行、且 clean_ratio<0.002 的容器 (靠 text_ratio 进来的) ---')
k5 = [x for x in k4 if x['clean_ratio'] < 0.002]
for x in sorted(k5, key=lambda y: -y['distinct'])[:20]:
    print('   %-8s d=%6d clean=%.6f tr=%.3f cjk2=%4d %-34s' %
          (x['kind'], x['distinct'], x['clean_ratio'], x['text_ratio'], x['cjk2'], x['name'][:34]))
