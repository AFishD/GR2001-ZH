# -*- coding: utf-8 -*-
"""r39 探针 11: 用新 debug 数据挑最终闸门 (sent_ratio 单判据 + word_ratio 诊断列)。只读。"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
D = json.load(open(os.path.join(HERE, 'container_debug.json'), encoding='utf-8'))
risky = [x for x in D if x['risk']]
safe = [x for x in D if not x['risk']]

print('--- 风险类: 新的 sent_ratio 分布 ---')
v = sorted(x['sent_ratio'] for x in risky)
q = lambda p: v[min(len(v) - 1, int(p * len(v)))]
print('   p50=%.3f p70=%.3f p80=%.3f p85=%.3f p90=%.3f p95=%.3f max=%.3f'
      % (q(.5), q(.7), q(.8), q(.85), q(.9), q(.95), v[-1]))

print('\n--- 候选闸门对比 (风险类) ---')
cands = [
    ('A 旧: d>=10 s>=10 sent>=.10', lambda x: x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .10),
    ('B: d>=10 s>=10 sent>=.15', lambda x: x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .15),
    ('C: d>=10 s>=10 sent>=.25', lambda x: x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .25),
    ('D: d>=10 s>=10 sent>=.15&w>=.5', lambda x: x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .15 and x['word_ratio'] >= .5),
    ('E: sent>=.15 或 (w>=.5 且 cjk2/msg 高)', lambda x: x['distinct'] >= 10 and x['score'] >= 10 and (x['sent_ratio'] >= .15 or (x['word_ratio'] >= .5 and x['msg'] >= 5))),
]
for (nm, f) in cands:
    keep = [x for x in risky if f(x)]
    cj = [x for x in keep if x['cjk2']]
    print('   %-38s 容器 %4d 串 %7d  cjk2>0: 容器 %3d 串 %6d'
          % (nm, len(keep), sum(x['distinct'] for x in keep), len(cj),
             sum(x['cjk2'] for x in cj)))

best = [x for x in risky if x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .15]
print('\n--- 候选 B 放行的容器 (%d), 按 kind ---' % len(best))
print('   %s' % dict(collections.Counter(x['kind'] for x in best)))
print('\n   前 30 个:')
for x in sorted(best, key=lambda y: -y['distinct'])[:30]:
    print('   %-8s d=%6d score=%8.2f sent=%.3f word=%.3f cjk2=%4d %-36s %9d B' %
          (x['kind'], x['distinct'], x['score'], x['sent_ratio'], x['word_ratio'],
           x['cjk2'], x['name'][:36], x['blob']))

print('\n--- B 里 cjk2>0 的容器 ---')
for x in sorted([y for y in best if y['cjk2']], key=lambda y: -y['cjk2'])[:20]:
    print('   %-8s d=%6d cjk2=%4d sent=%.3f %-36s %9d B' %
          (x['kind'], x['distinct'], x['cjk2'], x['sent_ratio'], x['name'][:36], x['blob']))

print('\n--- 被 B 拒掉、但旧门 A 放行 的容器 (会丢什么) ---')
lost = [x for x in risky if (x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .10)
        and not (x['distinct'] >= 10 and x['score'] >= 10 and x['sent_ratio'] >= .15)]
print('   数量 %d, 串 %d; 按 kind %s' %
      (len(lost), sum(x['distinct'] for x in lost), dict(collections.Counter(x['kind'] for x in lost))))
for x in sorted(lost, key=lambda y: -y['distinct'])[:20]:
    print('   %-8s d=%6d score=%8.2f sent=%.3f word=%.3f %-36s' %
          (x['kind'], x['distinct'], x['score'], x['sent_ratio'], x['word_ratio'], x['name'][:36]))

print('\n--- safe 类在 B 下的表现 (不设门, 但看 sent_ratio) ---')
for k in ('MIS', 'ATR', 'XML', 'RES', 'TXT', 'ELF', 'ISO_FILE'):
    rs = [x for x in safe if x['kind'] == k]
    lo = [x for x in rs if x['sent_ratio'] < .15]
    print('   %-9s %4d 个容器里 sent<0.15 的有 %3d  (若也上闸门会丢 %d 串)'
          % (k, len(rs), len(lo), sum(x['distinct'] for x in lo)))
